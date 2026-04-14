from rest_framework import generics, status, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.throttling import AnonRateThrottle
from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils.dateparse import parse_date
from .serializers import CustomTokenObtainPairSerializer, UserSerializer, ChangePasswordSerializer
from apps.core.models import Client
from apps.core.utils import ensure_pending_kyc_submission_for_client

User = get_user_model()


class LoginRateThrottle(AnonRateThrottle):
    rate = '5/minute'
    scope = 'login'


class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer
    throttle_classes = [LoginRateThrottle]

    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        if response.status_code == 200:
            # Attach user data to the response
            from rest_framework_simplejwt.tokens import AccessToken
            token = AccessToken(response.data['access'])
            user_id = token['user_id']
            try:
                user = User.objects.get(id=user_id)
                response.data['user'] = {
                    'id': user.id,
                    'username': user.username,
                    'email': user.email,
                    'role': user.role,
                    'name': user.get_full_name() or user.username,
                    'custom_permissions': user.custom_permissions,
                }
            except User.DoesNotExist:
                pass
            
            from apps.core.models import SystemLog
            SystemLog.objects.create(
                action="User Login",
                details=f"User {user.username} logged in successfully.",
                performed_by=user
            )

        return response


class UserListCreateView(generics.ListCreateAPIView):
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.role == 'ADMIN':
            return User.objects.all().order_by('-date_joined')
        return User.objects.filter(id=user.id)

    def get_permissions(self):
        if self.request.method == 'POST':
            return [permissions.IsAuthenticated()]
        return super().get_permissions()

    def perform_create(self, serializer):
        user = serializer.save()
        from apps.core.models import SystemLog
        SystemLog.objects.create(
            action="System User Created",
            details=f"Created {user.role} user: {user.username}.",
            performed_by=self.request.user
        )

class UserDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.role == 'ADMIN':
            return User.objects.all()
        return User.objects.filter(id=user.id)

    def perform_update(self, serializer):
        user = serializer.save()
        from apps.core.models import SystemLog
        SystemLog.objects.create(
            action="System User Updated",
            details=f"Updated details for user: {user.username}.",
            performed_by=self.request.user
        )

    def perform_destroy(self, instance):
        username = instance.username
        instance.delete()
        from apps.core.models import SystemLog
        SystemLog.objects.create(
            action="System User Deleted",
            details=f"Deleted user: {username}.",
            performed_by=self.request.user
        )

class MeView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        serializer = UserSerializer(request.user)
        return Response(serializer.data)


class ChangePasswordView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data)
        if serializer.is_valid():
            user = request.user
            if not user.check_password(serializer.validated_data['old_password']):
                return Response({'error': 'Wrong password'}, status=status.HTTP_400_BAD_REQUEST)
            user.set_password(serializer.validated_data['new_password'])
            user.save()
            
            from apps.core.models import SystemLog
            SystemLog.objects.create(
                action="Password Changed",
                details=f"User {user.username} changed their password.",
                performed_by=user
            )

            return Response({'message': 'Password changed successfully'})
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class LogoutView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        try:
            refresh_token = request.data.get('refresh')
            if refresh_token:
                token = RefreshToken(refresh_token)
                token.blacklist()
            
            from apps.core.models import SystemLog
            SystemLog.objects.create(
                action="User Logout",
                details=f"User {request.user.username} logged out.",
                performed_by=request.user
            )
            return Response({'message': 'Logged out successfully'})
        except Exception:
            return Response({'message': 'Logged out'})

class RegisterView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        data = request.data
        first_name = str(data.get('first_name', '')).strip()
        last_name = str(data.get('last_name', '')).strip()
        phone = str(data.get('phone', '')).strip()
        password = data.get('password')
        email = str(data.get('email', '')).strip() or f"{phone}@example.com"
        nrc_number = str(data.get('nrc_number', '')).strip() or None
        date_of_birth = parse_date(str(data.get('date_of_birth', '')).strip()) if data.get('date_of_birth') else None

        if not first_name or not phone or not password:
            return Response(
                {'error': 'First name, phone number, and password are required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if len(password) < 8:
            return Response(
                {'error': 'Password must be at least 8 characters long'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if User.objects.filter(username=phone).exists() or Client.objects.filter(phone=phone).exists():
            return Response({'error': 'User with this phone number already exists'}, status=status.HTTP_400_BAD_REQUEST)

        if Client.objects.filter(email__iexact=email).exists():
            return Response({'error': 'Client with this email address already exists'}, status=status.HTTP_400_BAD_REQUEST)

        if nrc_number and Client.objects.filter(nrc_number__iexact=nrc_number).exists():
            return Response({'error': 'Client with this NRC number already exists'}, status=status.HTTP_400_BAD_REQUEST)

        full_name = " ".join(part for part in [first_name, last_name] if part).strip() or phone

        with transaction.atomic():
            user = User.objects.create_user(
                username=phone,
                password=password,
                first_name=first_name,
                last_name=last_name,
                phone=phone,
                email=email,
                role='CLIENT'
            )

            client = Client.objects.create(
                user=user,
                name=full_name,
                email=email,
                phone=phone,
                nrc_number=nrc_number,
                date_of_birth=date_of_birth,
                address=data.get('address', ''),
                monthly_income=data.get('monthly_income') or 0,
                employment_status=data.get('employment_status') or 'EMPLOYED',
                employer_name=data.get('employer_name', ''),
                job_title=data.get('job_title', ''),
                gender=data.get('gender', ''),
                next_of_kin_name=data.get('next_of_kin_name', ''),
                next_of_kin_phone=data.get('next_of_kin_phone', ''),
                next_of_kin_relation=data.get('next_of_kin_relation', ''),
                kyc_verified=False,
            )
            ensure_pending_kyc_submission_for_client(client)

        from apps.core.models import SystemLog
        SystemLog.objects.create(
            action="New Client Registered",
            details=f"New client {full_name} registered with NRC {nrc_number or 'N/A'}.",
            performed_by=user
        )

        refresh = RefreshToken.for_user(user)
        access = refresh.access_token
        access['role'] = user.role
        access['email'] = user.email
        access['name'] = user.get_full_name() or user.username

        return Response({
            'message': 'Registration successful',
            'refresh': str(refresh),
            'access': str(access),
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'role': user.role,
                'name': user.get_full_name(),
            }
        }, status=status.HTTP_201_CREATED)


class ForgotPasswordView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        email = request.data.get('email', '').strip()
        if not email:
            return Response({'error': 'Email is required'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = User.objects.get(email__iexact=email)
        except User.DoesNotExist:
            # Don't reveal whether email exists
            return Response({'message': 'If that email is registered, a reset link has been sent.'})

        from .models import PasswordResetToken
        from .email_utils import send_system_email
        from django.conf import settings as django_settings

        # Invalidate old tokens
        PasswordResetToken.objects.filter(user=user, used=False).update(used=True)

        token_obj = PasswordResetToken.objects.create(user=user)
        reset_url = f"{django_settings.FRONTEND_URL}/?reset_token={token_obj.token}"

        subject = "Reset Your IntZam Password"
        text_body = f"Hi {user.get_full_name() or user.username},\n\nClick the link below to reset your password (valid for 1 hour):\n{reset_url}\n\nIf you did not request this, ignore this email."
        html_body = f"""
        <div style="font-family:Arial,sans-serif;max-width:480px;margin:0 auto;padding:32px;background:#f9fafb;border-radius:12px;">
            <div style="text-align:center;margin-bottom:24px;">
                <div style="display:inline-block;background:linear-gradient(135deg,#7c3aed,#5b21b6);color:white;font-weight:800;font-size:20px;width:48px;height:48px;line-height:48px;border-radius:12px;">IZ</div>
                <h2 style="color:#1f2937;margin:12px 0 0;">IntZam Loans</h2>
            </div>
            <h3 style="color:#1f2937;">Reset Your Password</h3>
            <p style="color:#6b7280;">Hi {user.get_full_name() or user.username},</p>
            <p style="color:#6b7280;">We received a request to reset your password. Click the button below to set a new password. This link expires in <strong>1 hour</strong>.</p>
            <div style="text-align:center;margin:32px 0;">
                <a href="{reset_url}" style="background:#7c3aed;color:white;padding:14px 32px;border-radius:8px;text-decoration:none;font-weight:600;display:inline-block;">Reset Password</a>
            </div>
            <p style="color:#9ca3af;font-size:13px;">If you didn't request a password reset, you can safely ignore this email.</p>
            <hr style="border:none;border-top:1px solid #e5e7eb;margin:24px 0;">
            <p style="color:#9ca3af;font-size:12px;text-align:center;">IntZam Micro Fin Limited</p>
        </div>
        """

        try:
            send_system_email(subject, text_body, html_body, [email])
        except Exception as e:
            return Response({'error': f'Failed to send email: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response({'message': 'If that email is registered, a reset link has been sent.'})


class ResetPasswordView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        token_str = request.data.get('token', '').strip()
        new_password = request.data.get('new_password', '').strip()

        if not token_str or not new_password:
            return Response({'error': 'Token and new password are required'}, status=status.HTTP_400_BAD_REQUEST)

        if len(new_password) < 8:
            return Response({'error': 'Password must be at least 8 characters'}, status=status.HTTP_400_BAD_REQUEST)

        from .models import PasswordResetToken
        try:
            import uuid
            token_obj = PasswordResetToken.objects.select_related('user').get(token=uuid.UUID(token_str))
        except (PasswordResetToken.DoesNotExist, ValueError):
            return Response({'error': 'Invalid or expired reset link'}, status=status.HTTP_400_BAD_REQUEST)

        if not token_obj.is_valid():
            return Response({'error': 'Reset link has expired. Please request a new one.'}, status=status.HTTP_400_BAD_REQUEST)

        user = token_obj.user
        user.set_password(new_password)
        user.save()
        token_obj.used = True
        token_obj.save()

        from apps.core.models import SystemLog
        SystemLog.objects.create(
            action="Password Reset",
            details=f"User {user.username} reset their password via email link.",
            performed_by=user
        )

        return Response({'message': 'Password reset successfully. You can now log in.'})
