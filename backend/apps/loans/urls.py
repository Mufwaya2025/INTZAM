from django.urls import path
from .views import (
    LoanListCreateView, LoanDetailView,
    ApproveLoanView, RejectLoanView, DisburseLoanView, ReturnToUnderwriterView,
    RepaymentView, PayoffQuoteView, SettleLoanView,
    RolloverEligibilityView, RolloverView, WriteOffLoanView, RecoveryView,
    RequestClientInfoView, ProvideClientInfoView,
    CollectionActivityListCreateView, LoanCalculatorView,
)

urlpatterns = [
    path('loans/', LoanListCreateView.as_view(), name='loan-list'),
    path('loans/<int:pk>/', LoanDetailView.as_view(), name='loan-detail'),
    path('loans/<int:pk>/approve/', ApproveLoanView.as_view(), name='loan-approve'),
    path('loans/<int:pk>/reject/', RejectLoanView.as_view(), name='loan-reject'),
    path('loans/<int:pk>/disburse/', DisburseLoanView.as_view(), name='loan-disburse'),
    path('loans/<int:pk>/return-to-underwriter/', ReturnToUnderwriterView.as_view(), name='loan-return-to-underwriter'),
    path('loans/<int:pk>/repay/', RepaymentView.as_view(), name='loan-repay'),
    path('loans/<int:pk>/payoff-quote/', PayoffQuoteView.as_view(), name='loan-payoff-quote'),
    path('loans/<int:pk>/settle/', SettleLoanView.as_view(), name='loan-settle'),
    path('loans/<int:pk>/rollover-eligibility/', RolloverEligibilityView.as_view(), name='loan-rollover-eligibility'),
    path('loans/<int:pk>/rollover/', RolloverView.as_view(), name='loan-rollover'),
    path('loans/<int:pk>/write-off/', WriteOffLoanView.as_view(), name='loan-write-off'),
    path('loans/<int:pk>/recover/', RecoveryView.as_view(), name='loan-recover'),
    path('loans/<int:pk>/request-info/', RequestClientInfoView.as_view(), name='loan-request-info'),
    path('loans/<int:pk>/provide-info/', ProvideClientInfoView.as_view(), name='loan-provide-info'),
    path('loans/<int:loan_pk>/activities/', CollectionActivityListCreateView.as_view(), name='loan-activities'),
    path('activities/', CollectionActivityListCreateView.as_view(), name='activity-list'),
    path('calculator/', LoanCalculatorView.as_view(), name='loan-calculator'),
]
