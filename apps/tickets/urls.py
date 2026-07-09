from rest_framework.routers import DefaultRouter

from apps.tickets.views import TicketViewSet


# DefaultRouter 会根据 ViewSet 自动生成 RESTful 路由。
# 注册后会得到：
# - GET /api/tickets/ 列表
# - POST /api/tickets/ 创建
# - GET /api/tickets/{id}/ 详情
# - PUT/PATCH /api/tickets/{id}/ 更新
# - DELETE /api/tickets/{id}/ 删除
router = DefaultRouter()
router.register('tickets', TicketViewSet, basename='ticket')

urlpatterns = router.urls
