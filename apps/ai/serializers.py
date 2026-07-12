from rest_framework import serializers


class TicketDraftRequestSerializer(serializers.Serializer):
    """工单草稿建议入参。"""

    raw_text = serializers.CharField(
        max_length=2000,
        trim_whitespace=True,
        help_text='用户输入的自然语言问题描述。',
    )


class TicketDraftResponseSerializer(serializers.Serializer):
    """工单草稿建议响应。"""

    title = serializers.CharField()
    description = serializers.CharField()
    category = serializers.CharField()
    priority = serializers.CharField()
    suggested_tags = serializers.ListField(child=serializers.CharField())
    checklist = serializers.ListField(child=serializers.CharField())
    confidence = serializers.FloatField()


class TicketAssistantResponseSerializer(serializers.Serializer):
    """已有工单智能处理建议响应。"""

    summary = serializers.CharField()
    next_actions = serializers.ListField(child=serializers.CharField())
    reply_template = serializers.CharField()
    recent_comments = serializers.ListField(child=serializers.CharField())
    attachment_count = serializers.IntegerField()
    confidence = serializers.FloatField()
