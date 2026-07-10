from drf_spectacular.utils import extend_schema
from rest_framework import generics, status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.users.serializers import ChangePasswordSerializer, RegisterSerializer, UserProfileSerializer


class RegisterView(generics.CreateAPIView):
    """用户注册接口。"""

    serializer_class = RegisterSerializer
    permission_classes = [AllowAny]


class MeView(generics.RetrieveUpdateAPIView):
    """当前登录用户信息接口。

    GET 用于查询个人资料；PATCH 用于更新邮箱、名和姓。
    """

    serializer_class = UserProfileSerializer

    def get_object(self):
        return self.request.user


class ChangePasswordView(APIView):
    """当前用户修改密码接口。"""

    @extend_schema(request=ChangePasswordSerializer, responses={200: None})
    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        request.user.set_password(serializer.validated_data['new_password'])
        request.user.save(update_fields=['password'])
        return Response({'detail': '密码修改成功。'}, status=status.HTTP_200_OK)
