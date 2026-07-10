from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework import serializers

from apps.tickets.models import Ticket, TicketAttachment, TicketComment, TicketStatus, TicketTag


User = get_user_model()


MAX_ATTACHMENT_SIZE = 5 * 1024 * 1024


# 工单状态流转白名单。
# 这样做的好处是后端明确控制业务流程，避免前端随便把已关闭工单改回待处理。
ALLOWED_STATUS_TRANSITIONS = {
    TicketStatus.OPEN: {TicketStatus.IN_PROGRESS, TicketStatus.CLOSED},
    TicketStatus.IN_PROGRESS: {TicketStatus.RESOLVED, TicketStatus.CLOSED},
    TicketStatus.RESOLVED: {TicketStatus.CLOSED},
    TicketStatus.CLOSED: set(),
}


class TicketSerializer(serializers.ModelSerializer):
    """工单接口序列化器。

    Serializer 负责把前端提交的 JSON 校验成可靠数据，也负责把数据库模型转换成接口响应。
    这里同时暴露用户 ID 和用户名：ID 方便前端提交，用户名方便接口阅读和调试。
    """

    # source='creator.username' 表示从关联的 creator 用户对象里取 username 字段。
    # read_only=True 表示这个字段只用于返回给前端，创建/更新时不允许前端直接提交。
    creator_username = serializers.CharField(source='creator.username', read_only=True)
    assignee_username = serializers.CharField(source='assignee.username', read_only=True)
    watcher_usernames = serializers.SerializerMethodField()
    tag_names = serializers.SerializerMethodField()

    # 处理人用用户 ID 提交即可，例如 {"assignee": 2}。
    # PrimaryKeyRelatedField 会检查这个 ID 对应的用户是否真的存在。
    assignee = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(),
        required=False,
        allow_null=True,
    )

    # 这两个字段来自 Ticket 模型里的 @property，不是数据库真实字段。
    # read_only=True 表示它们只负责展示计算结果。
    is_finished = serializers.BooleanField(read_only=True)
    is_overdue = serializers.BooleanField(read_only=True)

    class Meta:
        model = Ticket
        # fields 决定接口最终暴露哪些字段；没写在这里的模型字段不会出现在 API 响应里。
        fields = (
            'id',
            'title',
            'description',
            'category',
            'priority',
            'status',
            'creator',
            'creator_username',
            'assignee',
            'assignee_username',
            'watchers',
            'watcher_usernames',
            'tags',
            'tag_names',
            'due_at',
            'resolved_at',
            'closed_at',
            'created_at',
            'updated_at',
            'is_finished',
            'is_overdue',
        )
        # 创建人、创建时间、解决时间等字段应该由后端控制，不能交给前端随便传。
        read_only_fields = (
            'id',
            'creator',
            'creator_username',
            'assignee_username',
            'watchers',
            'watcher_usernames',
            'tag_names',
            'resolved_at',
            'closed_at',
            'created_at',
            'updated_at',
            'is_finished',
            'is_overdue',
        )

    def get_watcher_usernames(self, obj) -> list[str]:
        """返回关注人用户名列表，方便接口调试和前端直接展示。"""

        return [user.username for user in obj.watchers.all()]

    def get_tag_names(self, obj) -> list[str]:
        """返回标签名称列表，方便列表页直接展示。"""

        return [tag.name for tag in obj.tags.all()]

    def validate_status(self, value):
        """校验状态流转是否合法。"""

        # 创建工单时还没有旧状态，只需要检查字段枚举本身是否合法。
        if self.instance is None:
            return value

        old_status = self.instance.status
        if value == old_status:
            return value

        allowed_next_statuses = ALLOWED_STATUS_TRANSITIONS[old_status]
        if value not in allowed_next_statuses:
            raise serializers.ValidationError(
                f'工单状态不能从 {old_status} 直接流转到 {value}。'
            )

        return value

    def update(self, instance, validated_data):
        """更新工单，并在进入终态时自动记录时间。

        resolved_at 和 closed_at 不让前端直接传，是为了保证这些关键时间由后端统一维护。
        """

        old_status = instance.status
        ticket = super().update(instance, validated_data)

        if ticket.status != old_status:
            now = timezone.now()
            update_fields = []

            if ticket.status == TicketStatus.RESOLVED and ticket.resolved_at is None:
                ticket.resolved_at = now
                update_fields.append('resolved_at')

            if ticket.status == TicketStatus.CLOSED and ticket.closed_at is None:
                ticket.closed_at = now
                update_fields.append('closed_at')

            if update_fields:
                ticket.save(update_fields=update_fields)

        return ticket


class TicketCommentSerializer(serializers.ModelSerializer):
    """工单评论/处理记录序列化器。

    评论记录只允许前端提交 content 和 comment_type。
    ticket、author、created_at 都由后端根据当前请求自动确定，避免被伪造。
    """

    author_username = serializers.CharField(source='author.username', read_only=True)

    class Meta:
        model = TicketComment
        fields = (
            'id',
            'ticket',
            'author',
            'author_username',
            'content',
            'comment_type',
            'created_at',
        )
        read_only_fields = (
            'id',
            'ticket',
            'author',
            'author_username',
            'created_at',
        )


class TicketAttachmentSerializer(serializers.ModelSerializer):
    """工单附件序列化器。

    上传接口只需要前端提交 file，其他字段都由后端根据文件对象和当前用户自动补齐。
    这样可以避免前端伪造上传人、文件大小或所属工单。
    """

    uploaded_by_username = serializers.CharField(source='uploaded_by.username', read_only=True)

    class Meta:
        model = TicketAttachment
        fields = (
            'id',
            'ticket',
            'uploaded_by',
            'uploaded_by_username',
            'file',
            'original_filename',
            'content_type',
            'size',
            'created_at',
        )
        read_only_fields = (
            'id',
            'ticket',
            'uploaded_by',
            'uploaded_by_username',
            'original_filename',
            'content_type',
            'size',
            'created_at',
        )

    def validate_file(self, file):
        """限制第一版附件大小。

        文件上传如果不限制大小，恶意请求可能很快占满服务器磁盘。
        第一版先限制 5MB，后续可以改成环境变量或按文件类型分别配置。
        """

        if file.size > MAX_ATTACHMENT_SIZE:
            raise serializers.ValidationError('附件大小不能超过 5MB。')
        return file


class TicketAssignmentSerializer(serializers.Serializer):
    """工单分配接口序列化器。

    分配处理人是一个明确的业务动作，所以单独使用这个 Serializer 校验入参。
    这里允许 assignee 传 null，表示把工单从某个处理人手里取消分配。
    """

    assignee = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(),
        allow_null=True,
        required=True,
    )


class TicketTagSerializer(serializers.ModelSerializer):
    """工单标签序列化器。

    标签是可复用资源，创建后可以绑定到多张工单。
    """

    class Meta:
        model = TicketTag
        fields = ('id', 'name', 'color', 'created_at')
        read_only_fields = ('id', 'created_at')


class TicketTagAssignmentSerializer(serializers.Serializer):
    """设置工单标签的入参序列化器。

    前端提交标签 ID 列表即可，后端负责检查这些标签是否真实存在。
    """

    tags = serializers.PrimaryKeyRelatedField(
        queryset=TicketTag.objects.all(),
        many=True,
        required=True,
    )


class TicketReminderSerializer(serializers.Serializer):
    """工单催办接口入参。

    message 是可选补充说明，例如“客户已经二次催促，请优先处理”。
    """

    message = serializers.CharField(required=False, allow_blank=True, max_length=200)
