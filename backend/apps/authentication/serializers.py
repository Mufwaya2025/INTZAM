from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from django.contrib.auth import get_user_model
from apps.authentication.permission_utils import user_has_permission

User = get_user_model()


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token['role'] = user.role
        token['email'] = user.email
        token['name'] = user.get_full_name() or user.username
        return token

    def validate(self, attrs):
        # Allow login with email or phone number in addition to username
        identifier = attrs.get('username', '')
        if '@' in identifier or (identifier and not User.objects.filter(username=identifier).exists()):
            # Try email lookup
            user_qs = User.objects.filter(email__iexact=identifier)
            if not user_qs.exists():
                # Try phone lookup
                user_qs = User.objects.filter(phone=identifier)
            if user_qs.exists():
                attrs['username'] = user_qs.first().username

        data = super().validate(attrs)
        data['user'] = {
            'id': self.user.id,
            'username': self.user.username,
            'email': self.user.email,
            'role': self.user.role,
            'name': self.user.get_full_name() or self.user.username,
        }
        return data


class UserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=False)

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'role', 'phone', 'is_active', 'password', 'date_joined', 'last_login', 'custom_permissions']
        read_only_fields = ['id', 'date_joined', 'last_login']

    def get_fields(self):
        fields = super().get_fields()
        request = self.context.get('request')
        user = getattr(request, 'user', None)
        can_manage_users = bool(
            user and user.is_authenticated and user_has_permission(user, 'manage_users')
        )

        if not can_manage_users:
            for field_name in ['role', 'is_active', 'custom_permissions']:
                fields[field_name].read_only = True

        return fields

    def create(self, validated_data):
        password = validated_data.pop('password', None)
        user = User(**validated_data)
        if password:
            user.set_password(password)
        user.save()
        return user

    def update(self, instance, validated_data):
        password = validated_data.pop('password', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        if password:
            instance.set_password(password)
        instance.save()
        return instance


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True, min_length=8)
