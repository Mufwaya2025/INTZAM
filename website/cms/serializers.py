from rest_framework import serializers

from .models import (
    PublicLoanProduct,
    WebsiteAudience,
    WebsiteFAQ,
    WebsiteLead,
    WebsitePage,
    WebsitePageBlock,
    WebsitePageSection,
    WebsiteSettings,
    WebsiteTestimonial,
)


class AbsoluteMediaUrlMixin:
    def _build_media_url(self, file_field):
        if not file_field:
            return None
        request = self.context.get('request')
        url = file_field.url
        return request.build_absolute_uri(url) if request else url


class WebsiteSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = WebsiteSettings
        fields = '__all__'


class PublicLoanProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = PublicLoanProduct
        fields = '__all__'


class WebsiteAudienceSerializer(serializers.ModelSerializer):
    class Meta:
        model = WebsiteAudience
        fields = '__all__'


class WebsiteFAQSerializer(serializers.ModelSerializer):
    class Meta:
        model = WebsiteFAQ
        fields = '__all__'


class WebsiteTestimonialSerializer(serializers.ModelSerializer):
    class Meta:
        model = WebsiteTestimonial
        fields = '__all__'


class WebsitePageBlockSerializer(AbsoluteMediaUrlMixin, serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField()

    class Meta:
        model = WebsitePageBlock
        fields = '__all__'

    def get_image_url(self, obj):
        return self._build_media_url(obj.image)


class WebsitePageSectionSerializer(AbsoluteMediaUrlMixin, serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField()
    blocks = serializers.SerializerMethodField()

    class Meta:
        model = WebsitePageSection
        fields = '__all__'

    def get_image_url(self, obj):
        return self._build_media_url(obj.image)

    def get_blocks(self, obj):
        queryset = obj.blocks.filter(is_active=True)
        return WebsitePageBlockSerializer(queryset, many=True, context=self.context).data


class WebsitePageSerializer(AbsoluteMediaUrlMixin, serializers.ModelSerializer):
    hero_image_url = serializers.SerializerMethodField()
    illustration_image_url = serializers.SerializerMethodField()
    sections = serializers.SerializerMethodField()

    class Meta:
        model = WebsitePage
        fields = '__all__'

    def get_hero_image_url(self, obj):
        return self._build_media_url(obj.hero_image)

    def get_illustration_image_url(self, obj):
        return self._build_media_url(obj.illustration_image)

    def get_sections(self, obj):
        queryset = obj.sections.filter(is_active=True)
        return WebsitePageSectionSerializer(queryset, many=True, context=self.context).data


class WebsiteLeadSerializer(serializers.ModelSerializer):
    class Meta:
        model = WebsiteLead
        fields = '__all__'
        read_only_fields = ['id', 'status', 'created_at', 'updated_at']

    def validate_phone(self, value):
        cleaned = str(value).strip()
        if len(cleaned) < 8:
            raise serializers.ValidationError('Please enter a valid phone number.')
        return cleaned

    def validate(self, attrs):
        if not attrs.get('consent'):
            raise serializers.ValidationError({'consent': 'Consent is required before submitting your enquiry.'})
        return attrs
