"""FlowDesk 项目级路由。"""
from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView, SpectacularSwaggerView

urlpatterns = [
    path('admin/', admin.site.urls),
    # OpenAPI 原始 schema，机器可读，后续也可以给前端或接口测试工具导入。
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    # Swagger UI 更适合开发阶段手动调试接口。
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    # ReDoc 更适合阅读接口文档。
    path('api/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
    path('api/', include('apps.common.urls')),
    # 工单接口挂在 /api/ 下，实际路径由 apps.tickets.urls 里的 router 生成。
    path('api/', include('apps.tickets.urls')),
    path('api/users/', include('apps.users.urls')),
]
