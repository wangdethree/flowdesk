from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.ai.serializers import (
    TicketAssistantResponseSerializer,
    TicketDraftRequestSerializer,
    TicketDraftResponseSerializer,
)
from apps.ai.services import build_ticket_assistant_suggestion, build_ticket_draft
from apps.analytics.services import get_visible_ticket_queryset


class TicketDraftSuggestionView(APIView):
    """工单草稿智能建议接口。"""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary='生成工单草稿建议',
        description='根据自然语言描述生成标题、分类、优先级、建议标签和排查清单。',
        request=TicketDraftRequestSerializer,
        responses={200: TicketDraftResponseSerializer},
    )
    def post(self, request):
        serializer = TicketDraftRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        suggestion = build_ticket_draft(serializer.validated_data['raw_text'])
        return Response(suggestion)


class TicketAssistantSuggestionView(APIView):
    """已有工单智能处理建议接口。"""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary='生成已有工单处理建议',
        description='基于当前用户可见工单，生成摘要、下一步动作和回复模板。',
        responses={200: TicketAssistantResponseSerializer},
    )
    def get(self, request, pk):
        # 这里复用统计模块里的可见范围规则，避免普通用户通过 AI 接口读取无权工单。
        queryset = get_visible_ticket_queryset(request.user).select_related('assignee', 'creator')
        ticket = get_object_or_404(queryset, pk=pk)
        suggestion = build_ticket_assistant_suggestion(ticket)
        return Response(suggestion)
