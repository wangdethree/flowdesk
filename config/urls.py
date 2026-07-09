"""FlowDesk 项目级路由。"""
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('apps.common.urls')),
    # 工单接口挂在 /api/ 下，实际路径由 apps.tickets.urls 里的 router 生成。
    path('api/', include('apps.tickets.urls')),
    path('api/users/', include('apps.users.urls')),
]
