from rest_framework import generics
from rest_framework.permissions import AllowAny

from apps.users.serializers import RegisterSerializer, UserProfileSerializer


class RegisterView(generics.CreateAPIView):
    """用户注册接口。"""

    serializer_class = RegisterSerializer
    permission_classes = [AllowAny]


class MeView(generics.RetrieveAPIView):
    """当前登录用户信息接口。"""

    serializer_class = UserProfileSerializer

    def get_object(self):
        return self.request.user
