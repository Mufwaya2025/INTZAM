from django.urls import path
from .views import ReportView, DashboardStatsView

urlpatterns = [
    path('reports/<str:report_type>/', ReportView.as_view(), name='report'),
    path('dashboard/stats/', DashboardStatsView.as_view(), name='dashboard-stats'),
]
