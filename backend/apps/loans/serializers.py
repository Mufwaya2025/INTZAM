from decimal import Decimal

from rest_framework import serializers
from .models import Loan, LoanDocument, Transaction, CollectionActivity
from apps.core.serializers import ClientSerializer, KYCSubmissionSerializer, LoanProductSerializer
from apps.core.models import Client, KYCSection
from apps.core.utils import get_client_max_borrow_amount, get_client_qualified_record, sync_client_profile_for_user


QUALIFIED_BASE_REJECTION_MESSAGE = (
    "Sorry, you do not qualify for a loan at this time. "
    "If you believe this is an error, contact the our sales team."
)


class LoanDocumentSerializer(serializers.ModelSerializer):
    file_url = serializers.SerializerMethodField()

    class Meta:
        model = LoanDocument
        fields = ['id', 'file_name', 'file_url', 'uploaded_at']

    def get_file_url(self, obj):
        request = self.context.get('request')
        if obj.file:
            return request.build_absolute_uri(obj.file.url) if request else obj.file.url
        return None


class TransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Transaction
        fields = '__all__'
        read_only_fields = ['id', 'created_at']


class CollectionActivitySerializer(serializers.ModelSerializer):
    class Meta:
        model = CollectionActivity
        fields = '__all__'
        read_only_fields = ['id', 'created_at']


class LoanSerializer(serializers.ModelSerializer):
    client_name = serializers.CharField(source='client.name', read_only=True)
    client_email = serializers.CharField(source='client.email', read_only=True)
    product_name = serializers.CharField(source='product.name', read_only=True)
    repayment_frequency = serializers.CharField(source='product.repayment_frequency', read_only=True)
    outstanding_balance = serializers.ReadOnlyField()
    repayment_progress = serializers.ReadOnlyField()
    next_payment_due = serializers.ReadOnlyField()
    next_due_date = serializers.ReadOnlyField()
    client_details = ClientSerializer(source='client', read_only=True)
    latest_kyc_submission = serializers.SerializerMethodField()
    transactions = TransactionSerializer(many=True, read_only=True)
    collection_activities = CollectionActivitySerializer(many=True, read_only=True)
    info_documents = LoanDocumentSerializer(many=True, read_only=True)

    class Meta:
        model = Loan
        fields = '__all__'
        read_only_fields = ['id', 'loan_number', 'created_at', 'updated_at']

    def get_latest_kyc_submission(self, obj):
        submissions = list(obj.client.kyc_submissions.all())
        if not submissions:
            return None
        return KYCSubmissionSerializer(submissions[0]).data


class LoanCreateSerializer(serializers.ModelSerializer):
    client = serializers.PrimaryKeyRelatedField(
        queryset=Client.objects.all(),
        required=False
    )
    interest_rate = serializers.DecimalField(
        max_digits=6, decimal_places=2, required=False
    )
    documents = serializers.JSONField(required=False, default=list)

    class Meta:
        model = Loan
        fields = [
            'client', 'product', 'amount', 'purpose', 'term_months',
            'interest_rate', 'documents'
        ]

    @staticmethod
    def _has_active_kyc_form():
        return KYCSection.objects.filter(is_active=True, fields__isnull=False).exists()

    def validate(self, data):
        request = self.context.get('request')
        if not data.get('client') and request and hasattr(request.user, 'role') and request.user.role == 'CLIENT':
            data['client'] = sync_client_profile_for_user(request.user)
            
        if not data.get('client'):
            raise serializers.ValidationError({"client": "Client is required."})

        product = data['product']
        amount = data['amount']
        term = data.get('term_months') # might be missing if we just look at data directly, but it should be required by model

        if amount < product.min_amount or amount > product.max_amount:
            raise serializers.ValidationError(
                f"Amount must be between {product.min_amount} and {product.max_amount}"
            )
        if term < product.min_term or term > product.max_term:
            raise serializers.ValidationError(
                f"Term must be between {product.min_term} and {product.max_term} months"
            )

        client = data['client']
        if self._has_active_kyc_form() and not client.kyc_verified:
            latest_submission = client.kyc_submissions.order_by('-created_at').first()
            if latest_submission and latest_submission.status == 'APPROVED':
                client.kyc_verified = True
                client.save(update_fields=['kyc_verified'])
            elif latest_submission and latest_submission.status == 'PENDING':
                raise serializers.ValidationError("Your KYC application is currently under review.")
            else:
                raise serializers.ValidationError(
                    "You cannot borrow at this time. Please provide additional information to our office to qualify."
                )

        qualified = get_client_qualified_record(client)
        if not qualified or qualified.amount_qualified_for <= 0:
            raise serializers.ValidationError(QUALIFIED_BASE_REJECTION_MESSAGE)

        effective_max_amount = get_client_max_borrow_amount(client, product)
        if amount > effective_max_amount:
            raise serializers.ValidationError(
                f"You are only qualified to borrow up to ZMW {effective_max_amount:,.2f}."
            )

        return data

    def create(self, validated_data):
        from .services import calculate_loan_terms

        product = validated_data['product']
        amount = float(validated_data['amount'])
        term = validated_data['term_months']
        requested_rate = validated_data.get('interest_rate')
        stored_rate = requested_rate if requested_rate is not None else product.interest_rate

        pricing_kwargs = {}
        if requested_rate is None or Decimal(str(requested_rate)) == product.interest_rate:
            pricing_kwargs = {
                'nominal_interest_rate': product.nominal_interest_rate,
                'credit_facilitation_fee': product.credit_facilitation_fee,
                'processing_fee': product.processing_fee,
            }

        terms = calculate_loan_terms(
            amount,
            float(stored_rate),
            term,
            product.interest_type,
            repayment_frequency=product.repayment_frequency,
            **pricing_kwargs,
        )
        validated_data['interest_rate'] = stored_rate
        validated_data['total_repayable'] = terms['total_repayable']
        validated_data['monthly_payment'] = terms['monthly_payment']

        loan = Loan.objects.create(**validated_data)
        return loan
