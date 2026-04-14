import mimetypes
from pathlib import Path

from django.http import FileResponse, Http404
from django.views import View
from rest_framework import generics, permissions
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.models import LoanProduct, SystemLog
from apps.loans.services import calculate_loan_terms

from .models import (
    WebsiteAudience,
    WebsiteFAQ,
    WebsiteLead,
    WebsitePage,
    WebsiteSettings,
    WebsiteTestimonial,
    bootstrap_website_content,
)
from .serializers import (
    PublicLoanProductSerializer,
    WebsiteAudienceSerializer,
    WebsiteFAQSerializer,
    WebsiteLeadSerializer,
    WebsitePageSerializer,
    WebsiteSettingsSerializer,
    WebsiteTestimonialSerializer,
)


WEBSITE_DIR = Path(__file__).resolve().parents[3] / 'website'
ALLOWED_ASSETS = {'styles.css', 'script.js'}
ALLOWED_PAGES = {
    'about': 'about.html',
    'eligibility': 'eligibility.html',
    'civil-servants': 'civil-servants.html',
    'calculator': 'calculator.html',
    'contact': 'contact.html',
}


class PublicWebsiteIndexView(View):
    def get(self, request):
        index_path = WEBSITE_DIR / 'index.html'
        if not index_path.exists():
            raise Http404('Website index file not found.')
        return FileResponse(index_path.open('rb'), content_type='text/html; charset=utf-8')


class PublicWebsitePageView(View):
    def get(self, request, slug):
        filename = ALLOWED_PAGES.get(slug)
        if not filename:
            raise Http404('Website page not found.')

        page_path = WEBSITE_DIR / filename
        if not page_path.exists():
            raise Http404('Website page not found.')

        return FileResponse(page_path.open('rb'), content_type='text/html; charset=utf-8')


class PublicWebsiteAssetView(View):
    def get(self, request, filename):
        if filename not in ALLOWED_ASSETS:
            raise Http404('Asset not found.')

        file_path = WEBSITE_DIR / filename
        if not file_path.exists():
            raise Http404('Asset not found.')

        content_type = mimetypes.guess_type(str(file_path))[0] or 'text/plain'
        return FileResponse(file_path.open('rb'), content_type=content_type)


class WebsiteContentView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        bootstrap_website_content()
        settings = WebsiteSettings.get_solo()
        navigation_pages = WebsitePage.objects.filter(is_active=True, show_in_nav=True)

        payload = {
            'settings': WebsiteSettingsSerializer(settings).data,
            'products': PublicLoanProductSerializer(LoanProduct.objects.filter(is_active=True), many=True).data,
            'audiences': WebsiteAudienceSerializer(WebsiteAudience.objects.filter(is_active=True), many=True).data,
            'faqs': WebsiteFAQSerializer(WebsiteFAQ.objects.filter(is_active=True), many=True).data,
            'testimonials': WebsiteTestimonialSerializer(WebsiteTestimonial.objects.filter(is_active=True), many=True).data,
            'navigation_pages': WebsitePageSerializer(navigation_pages, many=True, context={'request': request}).data,
        }
        return Response(payload)


class WebsitePageDetailView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request, slug):
        bootstrap_website_content()
        try:
            page = WebsitePage.objects.get(slug=slug, is_active=True)
        except WebsitePage.DoesNotExist:
            return Response({'error': 'Website page not found.'}, status=status.HTTP_404_NOT_FOUND)

        serializer = WebsitePageSerializer(page, context={'request': request})
        return Response(serializer.data)


class WebsiteLeadCreateView(generics.CreateAPIView):
    serializer_class = WebsiteLeadSerializer
    queryset = WebsiteLead.objects.all()
    permission_classes = [permissions.AllowAny]

    def perform_create(self, serializer):
        lead = serializer.save(source_page='website')
        SystemLog.objects.create(
            action='Website Lead Submitted',
            details=f'Website lead captured: {lead.full_name} ({lead.phone}) - {lead.segment}.',
            performed_by=None,
        )


class WebsiteCalculatorView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        try:
            principal = float(request.data.get('principal', 0) or 0)
            term = int(request.data.get('term_months', 1) or 1)
        except (TypeError, ValueError):
            return Response({'error': 'Invalid calculator inputs.'}, status=status.HTTP_400_BAD_REQUEST)

        if principal <= 0 or term <= 0:
            return Response({'error': 'Principal and term must be greater than zero.'}, status=status.HTTP_400_BAD_REQUEST)

        product_id = request.data.get('product_id') or request.data.get('product')
        if not product_id:
            return Response({'error': 'Please select a loan product.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            product = LoanProduct.objects.get(pk=product_id, is_active=True)
        except (LoanProduct.DoesNotExist, TypeError, ValueError):
            return Response({'error': 'Loan product not found.'}, status=status.HTTP_404_NOT_FOUND)

        if principal < float(product.min_amount) or principal > float(product.max_amount):
            return Response(
                {'error': f'Amount must be between {product.min_amount} and {product.max_amount} for this product.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if term < product.min_term or term > product.max_term:
            return Response(
                {'error': f'Term must be between {product.min_term} and {product.max_term} months for this product.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        result = calculate_loan_terms(
            principal,
            float(product.interest_rate),
            term,
            product.interest_type,
            nominal_interest_rate=product.nominal_interest_rate,
            credit_facilitation_fee=product.credit_facilitation_fee,
            processing_fee=product.processing_fee,
        )
        result['product_name'] = product.name
        result['principal'] = principal
        result['term_months'] = term
        return Response(result)
