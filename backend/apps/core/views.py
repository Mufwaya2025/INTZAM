from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from django.db import transaction
from .models import Client, LoanProduct, SystemConfig
from .serializers import ClientSerializer, LoanProductSerializer, LoanProductWriteSerializer
from .utils import (
    ensure_pending_kyc_submission_for_client,
    ensure_pending_kyc_submissions_for_all_clients,
    sync_all_client_profiles,
    sync_client_profile_for_user,
)
from apps.authentication.permission_utils import user_has_permission


class IsAdminOrReadOnly(permissions.BasePermission):
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return request.user.is_authenticated
        if not request.user.is_authenticated:
            return False
        return (user_has_permission(request.user, 'manage_loan_products') or
                user_has_permission(request.user, 'manage_kyc_forms'))


class ClientListCreateView(generics.ListCreateAPIView):
    serializer_class = ClientSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.role == 'CLIENT':
            sync_client_profile_for_user(user)
            return Client.objects.filter(user=user)
        sync_all_client_profiles()
        return Client.objects.all()

    def perform_create(self, serializer):
        instance = serializer.save()
        from .models import SystemLog
        SystemLog.objects.create(
            action="Client Created",
            details=f"Admin created a new client: {instance.name} ({instance.email}).",
            performed_by=self.request.user
        )

class ClientDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = ClientSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.role == 'CLIENT':
            return Client.objects.filter(user=user)
        return Client.objects.all()


class LoanProductListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsAdminOrReadOnly]

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return LoanProductWriteSerializer
        return LoanProductSerializer

    def get_queryset(self):
        return LoanProduct.objects.filter(is_active=True)

    def perform_create(self, serializer):
        instance = serializer.save()
        from .models import SystemLog
        SystemLog.objects.create(
            action="Loan Product Created",
            details=f"Created new loan product: {instance.name}.",
            performed_by=self.request.user
        )


class LoanProductDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAdminOrReadOnly]

    def get_serializer_class(self):
        if self.request.method in ['PUT', 'PATCH']:
            return LoanProductWriteSerializer
        return LoanProductSerializer

    def get_queryset(self):
        return LoanProduct.objects.all()

    def perform_update(self, serializer):
        instance = serializer.save()
        from .models import SystemLog
        SystemLog.objects.create(
            action="Loan Product Updated",
            details=f"Updated loan product: {instance.name}.",
            performed_by=self.request.user
        )

class QualifiedBaseListCreateView(generics.ListCreateAPIView):
    permission_classes = [permissions.IsAuthenticated]
    from .models import QualifiedBase, SystemLog

    def get_serializer_class(self):
        from rest_framework import serializers
        class QualifiedBaseSerializer(serializers.ModelSerializer):
            class Meta:
                model = self.QualifiedBase
                fields = '__all__'
        return QualifiedBaseSerializer

    def get_queryset(self):
        from .models import QualifiedBase
        return QualifiedBase.objects.all()

    def perform_create(self, serializer):
        from .models import SystemLog
        instance = serializer.save()
        SystemLog.objects.create(
            action="Added to Qualified Base",
            details=f"Manually added {instance.nrc_number} to Qualified Base.",
            performed_by=self.request.user
        )


class QualifiedBaseEligibleClientsView(APIView):
    """Returns KYC-verified clients not yet in the Qualified Base."""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        from .models import QualifiedBase
        existing_nrcs = set(
            QualifiedBase.objects.exclude(nrc_number__isnull=True)
            .exclude(nrc_number='')
            .values_list('nrc_number', flat=True)
        )
        clients = Client.objects.filter(
            kyc_verified=True
        ).exclude(
            nrc_number__in=existing_nrcs
        ).exclude(nrc_number__isnull=True).exclude(nrc_number='')

        data = [
            {
                'id': c.id,
                'name': c.name,
                'phone': c.phone,
                'nrc_number': c.nrc_number,
                'email': c.email,
                'monthly_income': str(c.monthly_income),
                'employment_status': c.employment_status,
                'employer_name': c.employer_name,
            }
            for c in clients
        ]
        return Response(data)


class QualifiedBaseFromClientView(APIView):
    """Manually add a KYC-verified client to the Qualified Base with a required audit reason."""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        from .models import QualifiedBase, SystemLog

        client_id = request.data.get('client_id')
        amount = request.data.get('amount_qualified_for')
        reason = str(request.data.get('reason', '')).strip()
        product_name = str(request.data.get('product_name', '') or '').strip()

        if not client_id or not amount:
            return Response(
                {'error': 'client_id and amount_qualified_for are required.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        if not reason:
            return Response(
                {'error': 'A qualification reason is required for the audit trail.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            client = Client.objects.get(id=client_id)
        except Client.DoesNotExist:
            return Response({'error': 'Client not found.'}, status=status.HTTP_404_NOT_FOUND)

        if not client.kyc_verified:
            return Response(
                {'error': 'Client KYC has not been approved. Only KYC-verified clients can be added to the Qualified Base.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if QualifiedBase.objects.filter(nrc_number=client.nrc_number).exists():
            return Response(
                {'error': 'This client is already in the Qualified Base.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        name_parts = client.name.split(' ', 1)
        first_name = name_parts[0]
        last_name = name_parts[1] if len(name_parts) > 1 else ''

        record = QualifiedBase.objects.create(
            first_name=first_name,
            last_name=last_name,
            phone_number=client.phone,
            nrc_number=client.nrc_number,
            amount_qualified_for=amount,
        )

        product_detail = f" Product: {product_name}." if product_name else ""
        SystemLog.objects.create(
            action="Added to Qualified Base",
            details=(
                f"Manually added {client.name} (NRC: {client.nrc_number}) to Qualified Base. "
                f"Approved cap: ZMW {amount}.{product_detail} "
                f"Reason: {reason}"
            ),
            performed_by=request.user
        )

        return Response({
            'id': record.id,
            'first_name': record.first_name,
            'last_name': record.last_name,
            'phone_number': record.phone_number,
            'nrc_number': record.nrc_number,
            'amount_qualified_for': str(record.amount_qualified_for),
        }, status=status.HTTP_201_CREATED)

class QualifiedBaseUploadView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        if 'file' not in request.FILES:
            return Response({'error': 'No file provided'}, status=status.HTTP_400_BAD_REQUEST)
        
        file = request.FILES['file']
        if not file.name.endswith('.csv'):
            return Response({'error': 'File must be a CSV'}, status=status.HTTP_400_BAD_REQUEST)
            
        import csv
        from io import StringIO
        from .models import QualifiedBase, SystemLog
        
        decoded_file = file.read().decode('utf-8')
        io_string = StringIO(decoded_file)
        reader = csv.DictReader(io_string)
        
        success_count = 0
        error_count = 0
        for row in reader:
            try:
                QualifiedBase.objects.update_or_create(
                    nrc_number=row.get('nrc_number', '').strip(),
                    defaults={
                        'first_name': row.get('first_name', '').strip(),
                        'last_name': row.get('last_name', '').strip(),
                        'phone_number': row.get('phone_number', '').strip(),
                        'amount_qualified_for': float(row.get('amount_qualified_for', 0)),
                    }
                )
                success_count += 1
            except Exception:
                error_count += 1
                
        SystemLog.objects.create(
            action="Bulk Data Upload",
            details=f"Bulk uploaded Qualified Base data. {success_count} successful, {error_count} failed.",
            performed_by=request.user
        )
        
        return Response({
            'message': f'Upload complete. {success_count} records saved/updated, {error_count} errors.'
        }, status=status.HTTP_200_OK)

class SystemLogListView(generics.ListAPIView):
    permission_classes = [permissions.IsAuthenticated]
    
    def get_serializer_class(self):
        from rest_framework import serializers
        from .models import SystemLog
        class SystemLogSerializer(serializers.ModelSerializer):
            performed_by_name = serializers.CharField(source='performed_by.username', read_only=True)
            class Meta:
                model = SystemLog
                fields = '__all__'
        return SystemLogSerializer

    def get_queryset(self):
        if not user_has_permission(self.request.user, 'view_audit_logs'):
            from .models import SystemLog
            return SystemLog.objects.none()
        from .models import SystemLog
        return SystemLog.objects.all().order_by('-created_at')

# --- KYC Views ---

from .models import KYCSection, KYCField, KYCSubmission, KYCFieldValue
from .serializers import KYCSectionSerializer, KYCFieldSerializer, KYCSubmissionSerializer


def _delete_kyc_field_values(field_values):
    for field_value in field_values.select_related('submission', 'field'):
        if field_value.value_file:
            field_value.value_file.delete(save=False)
        field_value.delete()

class KYCSectionListCreateView(generics.ListCreateAPIView):
    permission_classes = [permissions.IsAuthenticated] # Clients can read, Admin write checks in method
    queryset = KYCSection.objects.all()
    serializer_class = KYCSectionSerializer

    def perform_create(self, serializer):
        if not user_has_permission(self.request.user, 'manage_kyc_forms'):
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("You do not have permission to manage KYC forms.")
        serializer.save()

class KYCSectionDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAdminOrReadOnly]
    queryset = KYCSection.objects.all()
    serializer_class = KYCSectionSerializer

    def perform_destroy(self, instance):
        with transaction.atomic():
            field_values = KYCFieldValue.objects.filter(field__section=instance)
            deleted_fields = KYCField.objects.filter(section=instance).count()
            deleted_responses = field_values.count()
            _delete_kyc_field_values(field_values)
            section_name = instance.name
            instance.delete()

        from .models import SystemLog
        SystemLog.objects.create(
            action="KYC Section Deleted",
            details=(
                f"Deleted KYC section '{section_name}' with "
                f"{deleted_fields} field(s) and {deleted_responses} response value(s)."
            ),
            performed_by=self.request.user
        )

class KYCFieldListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsAdminOrReadOnly]
    queryset = KYCField.objects.all()
    serializer_class = KYCFieldSerializer

class KYCFieldDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAdminOrReadOnly]
    queryset = KYCField.objects.all()
    serializer_class = KYCFieldSerializer

    def perform_destroy(self, instance):
        with transaction.atomic():
            field_values = KYCFieldValue.objects.filter(field=instance)
            deleted_responses = field_values.count()
            field_label = instance.label
            section_name = instance.section.name
            _delete_kyc_field_values(field_values)
            instance.delete()

        from .models import SystemLog
        SystemLog.objects.create(
            action="KYC Field Deleted",
            details=(
                f"Deleted KYC field '{field_label}' from section '{section_name}' "
                f"and removed {deleted_responses} response value(s)."
            ),
            performed_by=self.request.user
        )

class KYCSubmissionListCreateView(generics.ListCreateAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = KYCSubmissionSerializer

    def get_queryset(self):
        user = self.request.user
        if user.role == 'CLIENT':
            client = sync_client_profile_for_user(user)
            ensure_pending_kyc_submission_for_client(client)
            return KYCSubmission.objects.filter(client__user=user)
        ensure_pending_kyc_submissions_for_all_clients()
        return KYCSubmission.objects.all()

    def create(self, request, *args, **kwargs):
        # Format expects: { "fields": { field_id: "value", ... } }
        # Let's handle plain files and text
        user = request.user
        if user.role != 'CLIENT':
            return Response({'error': 'Only clients can submit KYC forms.'}, status=status.HTTP_400_BAD_REQUEST)

        client = sync_client_profile_for_user(user)
        if not client:
            return Response({'error': 'Client profile not found.'}, status=status.HTTP_404_NOT_FOUND)

        submission = KYCSubmission.objects.filter(client=client, status='PENDING').order_by('-created_at').first()
        if not submission:
            submission = KYCSubmission.objects.create(client=client)

        for key, value in request.data.items():
            if key.startswith('field_'):
                try:
                    field_id = int(key.split('_')[1])
                    field = KYCField.objects.get(id=field_id)
                    if field.field_type == 'FILE':
                        # Should be in request.FILES if it's a file
                        file_obj = request.FILES.get(key)
                        if file_obj:
                            existing_value = KYCFieldValue.objects.filter(submission=submission, field=field).first()
                            if existing_value and existing_value.value_file:
                                existing_value.value_file.delete(save=False)
                            KYCFieldValue.objects.update_or_create(
                                submission=submission,
                                field=field,
                                defaults={'value_file': file_obj, 'value_text': ''}
                            )
                    else:
                        KYCFieldValue.objects.update_or_create(
                            submission=submission,
                            field=field,
                            defaults={'value_text': str(value), 'value_file': None}
                        )
                except Exception:
                    pass

        serializer = self.get_serializer(submission)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

class KYCSubmissionDetailView(generics.RetrieveUpdateAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = KYCSubmissionSerializer
    queryset = KYCSubmission.objects.all()

    def perform_update(self, serializer):
        if not user_has_permission(self.request.user, 'review_kyc_submissions'):
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("You do not have permission to review KYC submissions.")

        instance = serializer.save(reviewed_by=self.request.user)
        if instance.status == 'APPROVED':
            client = instance.client
            client.kyc_verified = True
            client.save()


class SystemConfigView(APIView):
    """Get and update system configuration (admin only)."""
    permission_classes = [permissions.IsAuthenticated]

    SMTP_KEYS = ['smtp_host', 'smtp_port', 'smtp_username', 'smtp_password', 'smtp_use_tls', 'smtp_use_ssl', 'smtp_from_email']

    def get(self, request):
        if request.user.role != 'ADMIN':
            return Response({'error': 'Admin only'}, status=403)
        result = {}
        for key in self.SMTP_KEYS:
            try:
                result[key] = SystemConfig.objects.get(key=key).value
            except SystemConfig.DoesNotExist:
                result[key] = ''
        return Response(result)

    def post(self, request):
        if request.user.role != 'ADMIN':
            return Response({'error': 'Admin only'}, status=403)
        for key in self.SMTP_KEYS:
            if key in request.data:
                SystemConfig.objects.update_or_create(key=key, defaults={'value': request.data[key]})
        from apps.core.models import SystemLog
        SystemLog.objects.create(
            action="SMTP Config Updated",
            details="Admin updated SMTP email configuration.",
            performed_by=request.user
        )
        return Response({'message': 'Configuration saved'})


class TestEmailView(APIView):
    """Send a test email using current SMTP config."""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        if request.user.role != 'ADMIN':
            return Response({'error': 'Admin only'}, status=403)
        recipient = request.data.get('email') or request.user.email
        if not recipient:
            return Response({'error': 'No recipient email'}, status=400)

        from apps.authentication.email_utils import send_system_email
        try:
            send_system_email(
                subject="IntZam SMTP Test",
                text_body="This is a test email from IntZam LMS. Your SMTP configuration is working correctly.",
                html_body="""<div style="font-family:Arial,sans-serif;padding:24px;max-width:480px;">
                    <h2 style="color:#7c3aed;">IntZam LMS — SMTP Test</h2>
                    <p>Your SMTP configuration is working correctly.</p>
                    <p style="color:#6b7280;font-size:13px;">Sent from IntZam Micro Fin Limited</p>
                </div>""",
                recipient_list=[recipient],
            )
        except Exception as e:
            return Response({'error': str(e)}, status=500)

        return Response({'message': f'Test email sent to {recipient}'})
