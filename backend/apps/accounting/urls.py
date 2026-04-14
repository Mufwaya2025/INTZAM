from django.urls import path
from .views import (
    LedgerAccountListCreateView, LedgerAccountDetailView,
    JournalEntryListCreateView, JournalEntryDetailView,
    TrialBalanceView, OdooMonthlyReportView, MoMoWebhookView,
    KonseWebhookView,
)

urlpatterns = [
    path('accounting/accounts/', LedgerAccountListCreateView.as_view(), name='ledger-list'),
    path('accounting/accounts/<int:pk>/', LedgerAccountDetailView.as_view(), name='ledger-detail'),
    path('accounting/journal/', JournalEntryListCreateView.as_view(), name='journal-list'),
    path('accounting/journal/<int:pk>/', JournalEntryDetailView.as_view(), name='journal-detail'),
    path('accounting/trial-balance/', TrialBalanceView.as_view(), name='trial-balance'),
    path('accounting/odoo-monthly-report/', OdooMonthlyReportView.as_view(), name='odoo-monthly-report'),
    path('accounting/momo-webhook/', MoMoWebhookView.as_view(), name='momo-webhook'),
    path('accounting/konse-webhook/', KonseWebhookView.as_view(), name='konse-webhook'),
]
