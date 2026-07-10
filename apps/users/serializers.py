from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers


User = get_user_model()


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)
    password_confirm = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model = User
        fields = (
            'id',
            'username',
            'email',
            'password',
            'password_confirm',
        )
        read_only_fields = ('id',)

    def validate(self, attrs):
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError({'password_confirm': '两次输入的密码不一致。'})

        validate_password(attrs['password'])
        return attrs

    def create(self, validated_data):
        validated_data.pop('password_confirm')
        return User.objects.create_user(**validated_data)


class UserProfileSerializer(serializers.ModelSerializer):
    """当前用户资料序列化器。

    username 作为登录标识，第一版不允许用户自己修改。
    email、first_name、last_name 可以通过 PATCH /api/users/me/ 更新。
    """

    class Meta:
        model = User
        fields = (
            'id',
            'username',
            'email',
            'first_name',
            'last_name',
            'date_joined',
        )
        read_only_fields = ('id', 'username', 'date_joined')


class ChangePasswordSerializer(serializers.Serializer):
    """修改密码接口入参。

    修改密码必须校验旧密码，避免登录态被盗后直接静默改掉账号密码。
    """

    old_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True, min_length=8)
    new_password_confirm = serializers.CharField(write_only=True, min_length=8)

    def validate_old_password(self, value):
        """确认旧密码和当前用户密码一致。"""

        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError('旧密码不正确。')
        return value

    def validate(self, attrs):
        """确认两次新密码一致，并复用 Django 密码强度校验。"""

        if attrs['new_password'] != attrs['new_password_confirm']:
            raise serializers.ValidationError({'new_password_confirm': '两次输入的新密码不一致。'})

        validate_password(attrs['new_password'], self.context['request'].user)
        return attrs
