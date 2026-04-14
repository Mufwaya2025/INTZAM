from django.urls import path
from .views import AIRiskAnalysisView

urlpatterns = [
    path('ai/analyze/<int:loan_id>/', AIRiskAnalysisView.as_view(), name='ai-risk-analysis'),
]
