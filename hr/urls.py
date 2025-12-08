from django.urls import path

from hr.views.api.headcount_overview import HeadcountOverviewView

app_name = "hr"
urlpatterns = [
    path(
        "headcount/overview/",
        HeadcountOverviewView.as_view(),
        name="headcount-overview",
    ),
]
