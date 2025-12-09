from django.urls import path

from hr.views.api.headcount_overview import HeadcountOverviewView
from hr.views.api.compensation_overview import CompensationOverviewView
from hr.views.api.analytics import AnalyticsView
from hr.views.api.dashboard import HRDashboardView
from hr.views.api.headcount_breakdown import (
    HeadcountByDepartmentView,
    HeadcountByLocationView,
    HeadcountEmployeesView,
)
from hr.views.api.turnover import TurnoverView

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
        "headcount/by-department/",
        HeadcountByDepartmentView.as_view(),
        name="headcount-by-department",
    ),
    path(
        "headcount/by-location/",
        HeadcountByLocationView.as_view(),
        name="headcount-by-location",
    ),
    path(
        "headcount/employees/",
        HeadcountEmployeesView.as_view(),
        name="headcount-employees",
    ),
    # Turnover API
    path(
        "turnover/",
        TurnoverView.as_view(),
        name="turnover",
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
