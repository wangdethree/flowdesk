from django.db.models import Q
from drf_spectacular.utils import OpenApiParameter, OpenApiTypes, extend_schema, extend_schema_view
from rest_framework import filters, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.audit.models import AuditAction, AuditLog
from apps.audit.serializers import AuditLogSerializer
from apps.audit.services import create_audit_log
from apps.tickets.filters import TicketFilterBackend
from apps.tickets.models import Ticket, TicketTag
from apps.tickets.permissions import IsTicketParticipantOrStaff
from apps.tickets.serializers import (
    TicketAssignmentSerializer,
    TicketAttachmentSerializer,
    TicketCommentSerializer,
    TicketSerializer,
    TicketTagAssignmentSerializer,
    TicketTagSerializer,
)
from apps.tickets.services import (
    assign_ticket,
    notify_ticket_assigned,
    notify_ticket_commented,
    notify_ticket_status_changed,
)


@extend_schema_view(
    list=extend_schema(
        parameters=[
            OpenApiParameter('status', OpenApiTypes.STR, OpenApiParameter.QUERY, description='按工单状态筛选'),
            OpenApiParameter('priority', OpenApiTypes.STR, OpenApiParameter.QUERY, description='按优先级筛选'),
            OpenApiParameter('category', OpenApiTypes.STR, OpenApiParameter.QUERY, description='按分类筛选'),
            OpenApiParameter('assignee', OpenApiTypes.INT, OpenApiParameter.QUERY, description='按处理人用户 ID 筛选'),
            OpenApiParameter('creator', OpenApiTypes.INT, OpenApiParameter.QUERY, description='按创建人用户 ID 筛选'),
            OpenApiParameter('tag', OpenApiTypes.INT, OpenApiParameter.QUERY, description='按标签 ID 筛选'),
            OpenApiParameter('tag_name', OpenApiTypes.STR, OpenApiParameter.QUERY, description='按标签名称筛选'),
            OpenApiParameter('mine', OpenApiTypes.STR, OpenApiParameter.QUERY, description='筛选我的工单：created、assigned 或 watched'),
            OpenApiParameter('overdue', OpenApiTypes.BOOL, OpenApiParameter.QUERY, description='是否只看超时工单'),
            OpenApiParameter('has_assignee', OpenApiTypes.BOOL, OpenApiParameter.QUERY, description='是否只看已分配工单'),
            OpenApiParameter('search', OpenApiTypes.STR, OpenApiParameter.QUERY, description='按标题和描述搜索'),
            OpenApiParameter('ordering', OpenApiTypes.STR, OpenApiParameter.QUERY, description='排序字段，例如 -created_at'),
        ]
    ),
    retrieve=extend_schema(
        parameters=[
            OpenApiParameter(
                name='id',
                type=OpenApiTypes.INT,
                location=OpenApiParameter.PATH,
                description='工单 ID',
            )
        ]
    ),
    update=extend_schema(
        parameters=[
            OpenApiParameter(
                name='id',
                type=OpenApiTypes.INT,
                location=OpenApiParameter.PATH,
                description='工单 ID',
            )
        ]
    ),
    partial_update=extend_schema(
        parameters=[
            OpenApiParameter(
                name='id',
                type=OpenApiTypes.INT,
                location=OpenApiParameter.PATH,
                description='工单 ID',
            )
        ]
    ),
    destroy=extend_schema(
        parameters=[
            OpenApiParameter(
                name='id',
                type=OpenApiTypes.INT,
                location=OpenApiParameter.PATH,
                description='工单 ID',
            )
        ]
    ),
    assign=extend_schema(
        request=TicketAssignmentSerializer,
        responses=TicketSerializer,
        parameters=[
            OpenApiParameter(
                name='id',
                type=OpenApiTypes.INT,
                location=OpenApiParameter.PATH,
                description='工单 ID',
            )
        ],
    ),
    set_tags=extend_schema(
        request=TicketTagAssignmentSerializer,
        responses=TicketSerializer,
        parameters=[
            OpenApiParameter(
                name='id',
                type=OpenApiTypes.INT,
                location=OpenApiParameter.PATH,
                description='工单 ID',
            )
        ],
    ),
    watch=extend_schema(
        responses=TicketSerializer,
        parameters=[
            OpenApiParameter(
                name='id',
                type=OpenApiTypes.INT,
                location=OpenApiParameter.PATH,
                description='工单 ID',
            )
        ],
    ),
    unwatch=extend_schema(
        responses=TicketSerializer,
        parameters=[
            OpenApiParameter(
                name='id',
                type=OpenApiTypes.INT,
                location=OpenApiParameter.PATH,
                description='工单 ID',
            )
        ],
    ),
    audit_logs=extend_schema(
        responses=AuditLogSerializer(many=True),
        parameters=[
            OpenApiParameter(
                name='id',
                type=OpenApiTypes.INT,
                location=OpenApiParameter.PATH,
                description='工单 ID',
            )
        ],
    ),
    attachments=extend_schema(
        request=TicketAttachmentSerializer,
        responses=TicketAttachmentSerializer(many=True),
        parameters=[
            OpenApiParameter(
                name='id',
                type=OpenApiTypes.INT,
                location=OpenApiParameter.PATH,
                description='工单 ID',
            )
        ],
    ),
)
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

    # TicketFilterBackend 负责业务筛选；SearchFilter 支持 ?search=关键词；
    # OrderingFilter 支持 ?ordering=-created_at。
    filter_backends = [TicketFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['title', 'description']
    ordering_fields = ['created_at', 'updated_at', 'priority', 'status', 'due_at']
    ordering = ['-created_at']

    def get_serializer_class(self):
        """根据当前动作选择不同的 Serializer。"""

        # comments 是下面自定义的评论接口，输入输出结构和工单主表不同。
        if self.action == 'comments':
            return TicketCommentSerializer
        if self.action == 'attachments':
            return TicketAttachmentSerializer
        if self.action == 'audit_logs':
            return AuditLogSerializer
        if self.action == 'assign':
            return TicketAssignmentSerializer
        if self.action == 'set_tags':
            return TicketTagAssignmentSerializer
        return TicketSerializer

    def get_queryset(self):
        """返回当前用户可见的工单列表。

        管理员可以看到全部工单；普通用户只能看到自己创建或分配给自己的工单。
        具体查询参数筛选交给 TicketFilterBackend，这里只负责最核心的数据权限范围。
        """

        # drf-spectacular 生成接口文档时没有真实登录用户。
        # 返回空查询集可以让它安全读取模型信息，同时不影响真实请求的数据权限。
        if getattr(self, 'swagger_fake_view', False):
            return Ticket.objects.none()

        # select_related 会把 creator 和 assignee 一起查出来；prefetch_related 用于多对多关注人和标签。
        queryset = Ticket.objects.select_related('creator', 'assignee').prefetch_related(
            'watchers',
            'tags',
        )
        user = self.request.user

        # 普通用户只能看到“自己创建的工单”、“分配给自己的工单”或“自己关注的工单”。
        # Q 对象可以组合 OR 条件；这里的 | 就表示“或者”。
        if not user.is_staff:
            queryset = queryset.filter(
                Q(creator=user) | Q(assignee=user) | Q(watchers=user)
            ).distinct()

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
        if action == AuditAction.STATUS_CHANGE:
            notify_ticket_status_changed(
                ticket=ticket,
                actor=self.request.user,
                old_status=old_status,
                new_status=ticket.status,
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

    @action(detail=True, methods=['post'])
    def assign(self, request, pk=None):
        """分配或取消分配工单处理人。

        这个接口表示一个明确业务动作：POST /api/tickets/{id}/assign/。
        只有管理员和工单创建人可以分配处理人；当前处理人可以处理工单，但不能把工单转给别人。
        """

        # get_object 会先做数据范围和对象权限校验，无关用户拿到的是 404。
        ticket = self.get_object()

        if not request.user.is_staff and ticket.creator_id != request.user.id:
            return Response(
                {'detail': '只有管理员或工单创建人可以分配处理人。'},
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        assignee = serializer.validated_data['assignee']

        old_assignee_id = assign_ticket(ticket=ticket, assignee=assignee)
        create_audit_log(
            actor=request.user,
            action=AuditAction.ASSIGN,
            target=ticket,
            description='分配工单处理人',
            metadata={
                'old_assignee_id': old_assignee_id,
                'new_assignee_id': ticket.assignee_id,
            },
        )
        notify_ticket_assigned(ticket=ticket, actor=request.user)

        # 分配完成后返回完整工单，前端可以直接刷新当前详情页。
        return Response(TicketSerializer(ticket).data)

    @action(detail=True, methods=['post'], url_path='set-tags')
    def set_tags(self, request, pk=None):
        """设置某张工单的标签。

        标签会影响工单归类和筛选，所以第一版只允许管理员或工单创建人维护。
        """

        ticket = self.get_object()
        if not request.user.is_staff and ticket.creator_id != request.user.id:
            return Response(
                {'detail': '只有管理员或工单创建人可以设置标签。'},
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        ticket.tags.set(serializer.validated_data['tags'])
        return Response(TicketSerializer(ticket).data)

    @action(detail=True, methods=['post'])
    def watch(self, request, pk=None):
        """关注某张工单。

        关注后，用户可以在 mine=watched 里看到这张工单，并收到后续动态通知。
        """

        ticket = self.get_object()
        ticket.watchers.add(request.user)
        return Response(TicketSerializer(ticket).data)

    @action(detail=True, methods=['post'])
    def unwatch(self, request, pk=None):
        """取消关注某张工单。"""

        ticket = self.get_object()
        ticket.watchers.remove(request.user)
        return Response(TicketSerializer(ticket).data)

    @action(detail=True, methods=['get'], url_path='audit-logs')
    def audit_logs(self, request, pk=None):
        """查询某张工单的操作历史。

        审计日志本身是独立表，但这里挂在工单详情下面，是为了复用工单对象权限：
        只要用户不能查看这张工单，就不能查看这张工单的操作历史。
        """

        # get_object 会先限制当前用户能看到的工单范围，再做对象权限判断。
        # 因此无关用户访问别人工单的操作历史时，会和访问详情一样返回 404。
        ticket = self.get_object()
        logs = AuditLog.for_target(ticket).select_related('actor')

        page = self.paginate_queryset(logs)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(logs, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get', 'post'])
    def attachments(self, request, pk=None):
        """查询或上传某张工单下的附件。

        附件依附于工单，所以接口挂在 /api/tickets/{id}/attachments/。
        通过 get_object() 复用工单权限，确保无关用户不能查看或上传附件。
        """

        ticket = self.get_object()

        if request.method == 'GET':
            attachments = ticket.attachments.select_related('uploaded_by')
            page = self.paginate_queryset(attachments)
            if page is not None:
                serializer = self.get_serializer(page, many=True)
                return self.get_paginated_response(serializer.data)

            serializer = self.get_serializer(attachments, many=True)
            return Response(serializer.data)

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        uploaded_file = serializer.validated_data['file']
        attachment = serializer.save(
            ticket=ticket,
            uploaded_by=request.user,
            original_filename=uploaded_file.name,
            content_type=getattr(uploaded_file, 'content_type', ''),
            size=uploaded_file.size,
        )

        return Response(
            self.get_serializer(attachment).data,
            status=status.HTTP_201_CREATED,
        )

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
        notify_ticket_commented(ticket=ticket, comment=comment, actor=request.user)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class TicketTagViewSet(viewsets.ModelViewSet):
    """工单标签接口。

    标签本身是全局资源，登录用户都可以查看；第一版为了方便项目演示，也允许登录用户创建。
    真实公司内部系统里，可以再收紧为管理员维护。
    """

    serializer_class = TicketTagSerializer
    permission_classes = [IsAuthenticated]
    queryset = TicketTag.objects.all()
    search_fields = ['name']
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    ordering_fields = ['name', 'created_at']
    ordering = ['name']
