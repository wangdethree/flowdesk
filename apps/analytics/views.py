from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.analytics.services import get_ticket_summary


class TicketSummaryView(APIView):
    """工单统计摘要接口。

    这个接口只读，不修改任何业务数据。
    普通用户只能看到自己相关工单的统计结果，管理员能看到全局统计结果。
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary='工单统计摘要',
        description='返回当前用户可见范围内的工单数量、超时数量以及状态/优先级/分类分布。',
        responses={200: OpenApiResponse(description='工单统计摘要')},
    )
    def get(self, request):
        summary = get_ticket_summary(request.user)
        return Response(summary)
