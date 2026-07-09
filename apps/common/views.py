from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView


class HealthCheckView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        responses={
            200: OpenApiResponse(description='服务正常运行'),
        },
        summary='健康检查',
        description='用于确认 FlowDesk 后端服务是否正常响应。',
    )
    def get(self, request):
        return Response({
            'status': 'ok',
            'service': 'flowdesk',
            'message': 'FlowDesk API is running.',
        })
