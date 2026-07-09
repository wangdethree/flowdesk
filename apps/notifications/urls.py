from rest_framework.routers import DefaultRouter

from apps.notifications.views import NotificationViewSet


# 通知接口独立放在 /api/notifications/ 下，避免和工单主流程混在一起。
router = DefaultRouter()
router.register('notifications', NotificationViewSet, basename='notification')

urlpatterns = router.urls
