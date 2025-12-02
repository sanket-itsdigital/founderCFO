from django.urls import path

from litigation.views.api.dashboard_views import DashboardView
from litigation.views.api.case_views import (
    AllCasesListView,
    CaseDetailView,
    GSTCasesListView,
    IncomeTaxCasesListView,
    LabourPFCasesListView,
)
from litigation.views.api.analytics_views import AnalyticsView


app_name = "litigation"

urlpatterns = [
    path("dashboard/", DashboardView.as_view(), name="dashboard"),
    path("cases/", AllCasesListView.as_view(), name="cases-all"),
    path("cases/<uuid:pk>/", CaseDetailView.as_view(), name="cases-detail"),
    path("cases/gst/", GSTCasesListView.as_view(), name="cases-gst"),
    path(
        "cases/income-tax/", IncomeTaxCasesListView.as_view(), name="cases-income-tax"
    ),
    path("cases/labour-pf/", LabourPFCasesListView.as_view(), name="cases-labour-pf"),
    path("analytics/", AnalyticsView.as_view(), name="analytics"),
    
    
]
