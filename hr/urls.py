from django.urls import path

from hr.views.api.headcount_overview import HeadcountOverviewView
from hr.views.api.compensation_overview import CompensationOverviewView
from hr.views.api.analytics import AnalyticsView
from hr.views.api.dashboard import HRDashboardView

app_name = "hr"
urlpatterns = [
    path(
        "dashboard/",
        HRDashboardView.as_view(),
        name="dashboard",
    ),
    path(
        "headcount/overview/",
        HeadcountOverviewView.as_view(),
        name="headcount-overview",
    ),
    path(
        "compensation/overview/",
        CompensationOverviewView.as_view(),
        name="compensation-overview",
    ),
    path(
        "analytics/",
        AnalyticsView.as_view(),
        name="analytics",
    ),
]
