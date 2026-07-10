from django.urls import path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from apps.users.views import ChangePasswordView, MeView, RegisterView


urlpatterns = [
    path('register/', RegisterView.as_view(), name='user-register'),
    path('login/', TokenObtainPairView.as_view(), name='user-login'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token-refresh'),
    path('me/', MeView.as_view(), name='user-me'),
    path('change-password/', ChangePasswordView.as_view(), name='user-change-password'),
]
