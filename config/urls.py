"""FlowDesk 项目级路由。"""
from django.contrib import admin
from django.conf import settings
from django.conf.urls.static import static
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
    # 统计接口统一放在 /api/analytics/ 下，和工单 CRUD 主接口保持边界清晰。
    path('api/analytics/', include('apps.analytics.urls')),
    # 智能助手接口单独放在 /api/ai/ 下，后续替换成大模型实现时不会影响工单主接口。
    path('api/ai/', include('apps.ai.urls')),
    path('api/', include('apps.notifications.urls')),
    path('api/', include('apps.common.urls')),
    # 工单接口挂在 /api/ 下，实际路径由 apps.tickets.urls 里的 router 生成。
    path('api/', include('apps.tickets.urls')),
    path('api/users/', include('apps.users.urls')),
]

if settings.DEBUG:
    # 本地开发时让 Django 直接提供上传文件，方便前端点击附件链接进行验收。
    # 生产环境不要依赖这个能力，应该由 Nginx、CDN 或对象存储负责静态文件分发。
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
