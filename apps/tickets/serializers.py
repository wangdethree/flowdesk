from django.contrib.auth import get_user_model
from rest_framework import serializers

from apps.tickets.models import Ticket


User = get_user_model()


class TicketSerializer(serializers.ModelSerializer):
    """工单接口序列化器。

    Serializer 负责把前端提交的 JSON 校验成可靠数据，也负责把数据库模型转换成接口响应。
    这里同时暴露用户 ID 和用户名：ID 方便前端提交，用户名方便接口阅读和调试。
    """

    # source='creator.username' 表示从关联的 creator 用户对象里取 username 字段。
    # read_only=True 表示这个字段只用于返回给前端，创建/更新时不允许前端直接提交。
    creator_username = serializers.CharField(source='creator.username', read_only=True)
    assignee_username = serializers.CharField(source='assignee.username', read_only=True)

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
            'resolved_at',
            'closed_at',
            'created_at',
            'updated_at',
            'is_finished',
            'is_overdue',
        )
