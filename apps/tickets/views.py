from django.db.models import Q
from rest_framework import filters, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.audit.models import AuditAction
from apps.audit.services import create_audit_log
from apps.tickets.models import Ticket
from apps.tickets.permissions import IsTicketParticipantOrStaff
from apps.tickets.serializers import TicketCommentSerializer, TicketSerializer


class TicketViewSet(viewsets.ModelViewSet):
    """工单 CRUD 接口。

    ModelViewSet 会自动提供列表、创建、详情、更新、局部更新和删除能力。
    我们在这里主要补三件事：限制用户可见数据、支持常用筛选、创建时自动绑定创建人。
    """

    # serializer_class 决定这个 ViewSet 用哪个 Serializer 做入参校验和响应转换。
    serializer_class = TicketSerializer
    # permission_classes 决定访问接口时需要经过哪些权限判断。
    # IsAuthenticated 先保证“必须登录”，IsTicketParticipantOrStaff 再判断“能不能访问这张工单”。
    permission_classes = [IsAuthenticated, IsTicketParticipantOrStaff]

    # SearchFilter 支持 ?search=关键词，OrderingFilter 支持 ?ordering=-created_at。
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['title', 'description']
    ordering_fields = ['created_at', 'updated_at', 'priority', 'status', 'due_at']
    ordering = ['-created_at']

    def get_serializer_class(self):
        """根据当前动作选择不同的 Serializer。"""

        # comments 是下面自定义的评论接口，输入输出结构和工单主表不同。
        if self.action == 'comments':
            return TicketCommentSerializer
        return TicketSerializer

    def get_queryset(self):
        """返回当前用户可见的工单列表。

        管理员可以看到全部工单；普通用户只能看到自己创建或分配给自己的工单。
        这里先手写少量筛选逻辑，避免第一版过早引入额外依赖。
        """

        # select_related 会把 creator 和 assignee 一起查出来，减少后续访问用户名时的额外查询。
        queryset = Ticket.objects.select_related('creator', 'assignee')
        user = self.request.user

        # 普通用户只能看到“自己创建的工单”或“分配给自己的工单”。
        # Q 对象可以组合 OR 条件；这里的 | 就表示“或者”。
        if not user.is_staff:
            queryset = queryset.filter(Q(creator=user) | Q(assignee=user))

        # query_params 对应 URL 问号后面的查询参数，例如 /api/tickets/?status=open。
        status = self.request.query_params.get('status')
        priority = self.request.query_params.get('priority')
        category = self.request.query_params.get('category')
        assignee = self.request.query_params.get('assignee')

        # 下面这些筛选条件都是可选的：传了才筛，不传就忽略。
        if status:
            queryset = queryset.filter(status=status)
        if priority:
            queryset = queryset.filter(priority=priority)
        if category:
            queryset = queryset.filter(category=category)
        if assignee:
            queryset = queryset.filter(assignee_id=assignee)

        return queryset

    def perform_create(self, serializer):
        """创建工单时以后端当前登录用户作为创建人，避免前端伪造 creator。"""

        # serializer.save() 会调用 Serializer 的 create/update 逻辑，并最终写入数据库。
        # 这里强制使用 request.user，前端即使传 creator 字段也不会生效。
        ticket = serializer.save(creator=self.request.user)
        create_audit_log(
            actor=self.request.user,
            action=AuditAction.CREATE,
            target=ticket,
            description='创建工单',
            metadata={'title': ticket.title, 'status': ticket.status},
        )

    def perform_update(self, serializer):
        """更新工单后写审计日志。

        这里先记录状态和标题等关键字段。更细粒度的字段 diff 可以放到后续版本增强。
        """

        old_status = serializer.instance.status
        ticket = serializer.save()
        action = AuditAction.STATUS_CHANGE if ticket.status != old_status else AuditAction.UPDATE
        description = '变更工单状态' if action == AuditAction.STATUS_CHANGE else '更新工单'
        create_audit_log(
            actor=self.request.user,
            action=action,
            target=ticket,
            description=description,
            metadata={
                'title': ticket.title,
                'old_status': old_status,
                'new_status': ticket.status,
            },
        )

    def perform_destroy(self, instance):
        """删除工单前写审计日志。

        删除后对象不再存在，所以要在真正 delete 之前先记录标题和状态。
        """

        create_audit_log(
            actor=self.request.user,
            action=AuditAction.DELETE,
            target=instance,
            description='删除工单',
            metadata={'title': instance.title, 'status': instance.status},
        )
        instance.delete()

    @action(detail=True, methods=['get', 'post'])
    def comments(self, request, pk=None):
        """查询或新增某张工单下的评论/处理记录。

        这个接口挂在工单详情下面：/api/tickets/{id}/comments/。
        这样设计是因为评论本身依附于某张工单，不适合作为孤立资源随便创建。
        """

        # get_object 会先走 get_queryset 的数据范围限制，再走对象权限校验。
        # 所以无关用户既看不到工单，也不能给工单写评论。
        ticket = self.get_object()

        if request.method == 'GET':
            comments = ticket.comments.select_related('author')
            page = self.paginate_queryset(comments)
            if page is not None:
                serializer = self.get_serializer(page, many=True)
                return self.get_paginated_response(serializer.data)

            serializer = self.get_serializer(comments, many=True)
            return Response(serializer.data)

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        comment = serializer.save(ticket=ticket, author=request.user)
        create_audit_log(
            actor=request.user,
            action=AuditAction.COMMENT,
            target=ticket,
            description='新增工单记录',
            metadata={
                'comment_id': comment.id,
                'comment_type': comment.comment_type,
            },
        )
        return Response(serializer.data, status=status.HTTP_201_CREATED)
