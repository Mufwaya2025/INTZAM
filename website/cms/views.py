import mimetypes
from pathlib import Path

from django.http import FileResponse, Http404
from django.views import View
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import PublicLoanProduct, WebsiteAudience, WebsiteFAQ, WebsiteLead, WebsitePage, WebsiteSettings, WebsiteTestimonial, bootstrap_website_content, calculate_loan_terms
from .serializers import (
    PublicLoanProductSerializer,
    WebsiteAudienceSerializer,
    WebsiteFAQSerializer,
    WebsiteLeadSerializer,
    WebsitePageSerializer,
    WebsiteSettingsSerializer,
    WebsiteTestimonialSerializer,
)


WEBSITE_DIR = Path(__file__).resolve().parents[1]
ALLOWED_ASSETS = {'styles.css', 'script.js'}
ALLOWED_PAGES = {
    'about': 'about.html',
    'eligibility': 'eligibility.html',
    'civil-servants': 'civil-servants.html',
    'calculator': 'calculator.html',
    'contact': 'contact.html',
    'privacy': 'privacy.html',
    'terms': 'terms.html',
}


class PublicWebsiteIndexView(View):
    def get(self, request):
        file_path = WEBSITE_DIR / 'index.html'
        if not file_path.exists():
            raise Http404('Website index file not found.')
        return FileResponse(file_path.open('rb'), content_type='text/html; charset=utf-8')


class PublicWebsitePageView(View):
    def get(self, request, slug):
        filename = ALLOWED_PAGES.get(slug)
        if not filename:
            raise Http404('Website page not found.')
        file_path = WEBSITE_DIR / filename
        if not file_path.exists():
            raise Http404('Website page not found.')
        return FileResponse(file_path.open('rb'), content_type='text/html; charset=utf-8')


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
            'products': PublicLoanProductSerializer(PublicLoanProduct.objects.filter(is_active=True), many=True).data,
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
        return Response(WebsitePageSerializer(page, context={'request': request}).data)


class WebsiteLeadCreateView(generics.CreateAPIView):
    serializer_class = WebsiteLeadSerializer
    queryset = WebsiteLead.objects.all()
    permission_classes = [permissions.AllowAny]

    def perform_create(self, serializer):
        serializer.save(source_page=self.request.data.get('source_page') or 'website')


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
            product = PublicLoanProduct.objects.get(pk=product_id, is_active=True)
        except (PublicLoanProduct.DoesNotExist, TypeError, ValueError):
            return Response({'error': 'Loan product not found.'}, status=status.HTTP_404_NOT_FOUND)

        if principal < float(product.min_amount) or principal > float(product.max_amount):
            return Response({'error': f'Amount must be between {product.min_amount} and {product.max_amount} for this product.'}, status=status.HTTP_400_BAD_REQUEST)

        if term < product.min_term or term > product.max_term:
            return Response({'error': f'Term must be between {product.min_term} and {product.max_term} months for this product.'}, status=status.HTTP_400_BAD_REQUEST)

        result = calculate_loan_terms(
            principal,
            float(product.interest_rate),
            term,
            product.interest_type,
            nominal_interest_rate=float(product.nominal_interest_rate),
            credit_facilitation_fee=float(product.credit_facilitation_fee),
            processing_fee=float(product.processing_fee),
        )
        result['product_name'] = product.name
        result['principal'] = principal
        result['term_months'] = term
        result['interest_rate'] = float(product.interest_rate)
        result['nominal_interest_rate'] = float(product.nominal_interest_rate)
        result['credit_facilitation_fee'] = float(product.credit_facilitation_fee)
        result['processing_fee'] = float(product.processing_fee)
        return Response(result)
