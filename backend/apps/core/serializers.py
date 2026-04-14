from rest_framework import serializers
from .models import Client, LoanProduct, TierConfig, KYCSection, KYCField, KYCSubmission, KYCFieldValue
from .utils import get_client_max_borrow_amount


class TierConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model = TierConfig
        fields = ['id', 'tier', 'interest_rate', 'max_limit_multiplier']


class ClientSerializer(serializers.ModelSerializer):
    vetting_status = serializers.SerializerMethodField()

    class Meta:
        model = Client
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at', 'tier', 'completed_loans']

    def get_vetting_status(self, obj):
        if obj.kyc_verified:
            return "Verified"
        # Since we order submissions by -created_at, we just grab the first one
        sub = obj.kyc_submissions.first()
        if sub:
            return sub.status
        return "Not Submitted"


class LoanProductSerializer(serializers.ModelSerializer):
    tiers = TierConfigSerializer(many=True, read_only=True)
    client_max_borrow_amount = serializers.SerializerMethodField()

    class Meta:
        model = LoanProduct
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_client_max_borrow_amount(self, obj):
        request = self.context.get('request')
        user = getattr(request, 'user', None)

        if not user or not user.is_authenticated or getattr(user, 'role', None) != 'CLIENT':
            return None

        client = getattr(user, 'client_profile', None)
        if not client:
            return 0

        return float(get_client_max_borrow_amount(client, obj))


class LoanProductWriteSerializer(serializers.ModelSerializer):
    tiers = TierConfigSerializer(many=True, required=False)

    class Meta:
        model = LoanProduct
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']

    def create(self, validated_data):
        tiers_data = validated_data.pop('tiers', [])
        product = LoanProduct.objects.create(**validated_data)
        for tier_data in tiers_data:
            TierConfig.objects.create(product=product, **tier_data)
        return product

    def update(self, instance, validated_data):
        tiers_data = validated_data.pop('tiers', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        if tiers_data is not None:
            instance.tiers.all().delete()
            for tier_data in tiers_data:
                TierConfig.objects.create(product=instance, **tier_data)
        return instance

class KYCFieldSerializer(serializers.ModelSerializer):
    class Meta:
        model = KYCField
        fields = '__all__'

class KYCSectionSerializer(serializers.ModelSerializer):
    fields = KYCFieldSerializer(many=True, read_only=True)

    class Meta:
        model = KYCSection
        fields = '__all__'

class KYCFieldValueSerializer(serializers.ModelSerializer):
    field_name = serializers.CharField(source='field.name', read_only=True)
    field_label = serializers.CharField(source='field.label', read_only=True)
    field_type = serializers.CharField(source='field.field_type', read_only=True)

    class Meta:
        model = KYCFieldValue
        fields = '__all__'

class KYCSubmissionSerializer(serializers.ModelSerializer):
    field_values = KYCFieldValueSerializer(many=True, read_only=True)
    client_name = serializers.CharField(source='client.name', read_only=True)
    client_details = ClientSerializer(source='client', read_only=True)

    class Meta:
        model = KYCSubmission
        fields = '__all__'

