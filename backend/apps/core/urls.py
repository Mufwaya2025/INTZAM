from django.urls import path
from .views import (
    ClientListCreateView, ClientDetailView,
    LoanProductListCreateView, LoanProductDetailView,
    QualifiedBaseListCreateView, QualifiedBaseUploadView,
    QualifiedBaseEligibleClientsView, QualifiedBaseFromClientView,
    SystemLogListView,
    KYCSectionListCreateView, KYCSectionDetailView,
    KYCFieldListCreateView, KYCFieldDetailView,
    KYCSubmissionListCreateView, KYCSubmissionDetailView,
    SystemConfigView, TestEmailView,
)

urlpatterns = [
    path('clients/', ClientListCreateView.as_view(), name='client-list'),
    path('clients/<int:pk>/', ClientDetailView.as_view(), name='client-detail'),
    path('products/', LoanProductListCreateView.as_view(), name='product-list'),
    path('products/<int:pk>/', LoanProductDetailView.as_view(), name='product-detail'),
    path('qualified-base/', QualifiedBaseListCreateView.as_view(), name='qualified-base-list'),
    path('qualified-base/upload/', QualifiedBaseUploadView.as_view(), name='qualified-base-upload'),
    path('qualified-base/eligible-clients/', QualifiedBaseEligibleClientsView.as_view(), name='qualified-base-eligible'),
    path('qualified-base/from-client/', QualifiedBaseFromClientView.as_view(), name='qualified-base-from-client'),
    path('audit-logs/', SystemLogListView.as_view(), name='audit-logs'),
    
    # KYC URLs
    path('kyc/sections/', KYCSectionListCreateView.as_view(), name='kyc-section-list'),
    path('kyc/sections/<int:pk>/', KYCSectionDetailView.as_view(), name='kyc-section-detail'),
    path('kyc/fields/', KYCFieldListCreateView.as_view(), name='kyc-field-list'),
    path('kyc/fields/<int:pk>/', KYCFieldDetailView.as_view(), name='kyc-field-detail'),
    path('kyc/submissions/', KYCSubmissionListCreateView.as_view(), name='kyc-submission-list'),
    path('kyc/submissions/<int:pk>/', KYCSubmissionDetailView.as_view(), name='kyc-submission-detail'),

    # Settings / SMTP
    path('settings/smtp/', SystemConfigView.as_view(), name='system-config'),
    path('settings/test-email/', TestEmailView.as_view(), name='test-email'),
]
