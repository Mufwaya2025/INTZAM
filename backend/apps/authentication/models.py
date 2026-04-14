import uuid
from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone


class UserRole(models.TextChoices):
    ADMIN = 'ADMIN', 'Admin'
    PORTFOLIO_MANAGER = 'PORTFOLIO_MANAGER', 'Portfolio Manager'
    COLLECTIONS_OFFICER = 'COLLECTIONS_OFFICER', 'Collections Officer'
    ACCOUNTANT = 'ACCOUNTANT', 'Accountant'
    UNDERWRITER = 'UNDERWRITER', 'Underwriter'
    CLIENT = 'CLIENT', 'Client'


class User(AbstractUser):
    role = models.CharField(max_length=30, choices=UserRole.choices, default=UserRole.CLIENT)
    phone = models.CharField(max_length=20, blank=True)
    is_active = models.BooleanField(default=True)
    custom_permissions = models.JSONField(default=list, blank=True)

    class Meta:
        db_table = 'auth_user'

    def __str__(self):
        return f"{self.username} ({self.role})"

    @property
    def is_staff_member(self):
        return self.role in [
            UserRole.ADMIN,
            UserRole.PORTFOLIO_MANAGER,
            UserRole.COLLECTIONS_OFFICER,
            UserRole.ACCOUNTANT,
            UserRole.UNDERWRITER,
        ]


class PasswordResetToken(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='reset_tokens')
    token = models.UUIDField(default=uuid.uuid4, unique=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    used = models.BooleanField(default=False)

    class Meta:
        db_table = 'password_reset_tokens'

    def is_valid(self):
        return not self.used and (timezone.now() - self.created_at).total_seconds() < 3600
