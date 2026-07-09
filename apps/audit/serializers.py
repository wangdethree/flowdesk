from rest_framework import serializers

from apps.audit.models import AuditLog


class AuditLogSerializer(serializers.ModelSerializer):
    """审计日志序列化器。

    审计日志主要用于展示“谁在什么时候对哪个资源做了什么操作”。
    actor_username 是给前端和接口调试看的冗余展示字段，真正关联仍然用 actor 用户 ID。
    """

    actor_username = serializers.CharField(source='actor.username', read_only=True)
    action_display = serializers.CharField(source='get_action_display', read_only=True)

    class Meta:
        model = AuditLog
        fields = (
            'id',
            'actor',
            'actor_username',
            'action',
            'action_display',
            'target_type',
            'target_id',
            'description',
            'metadata',
            'created_at',
        )
        read_only_fields = fields
