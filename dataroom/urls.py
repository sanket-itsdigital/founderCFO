from django.urls import path

from dataroom.views.api.overview_views import OverviewView
from dataroom.views.api.folder_views import (
    FolderListCreateView,
    FolderRetrieveUpdateView,
)
from dataroom.views.api.document_views import (
    DocumentListCreateView,
    DocumentRetrieveUpdateView,
    FolderDocumentsView,
    DocumentVersionListCreateView,
    VersionCompareView,
)
from dataroom.views.api.qa_views import (
    QuestionListCreateView,
    QuestionRetrieveUpdateView,
)
from dataroom.views.api.access_log_views import AccessLogListView

app_name = "dataroom"

urlpatterns = [
    path("overview/", OverviewView.as_view(), name="overview"),
    path("folders/", FolderListCreateView.as_view(), name="folders"),
    path(
        "folders/<uuid:pk>/", FolderRetrieveUpdateView.as_view(), name="folder-detail"
    ),
    path(
        "folders/<uuid:folder_id>/documents/",
        FolderDocumentsView.as_view(),
        name="folder-documents",
    ),
    path("documents/", DocumentListCreateView.as_view(), name="documents"),
    path(
        "documents/<uuid:pk>/",
        DocumentRetrieveUpdateView.as_view(),
        name="document-detail",
    ),
    path("versions/", DocumentVersionListCreateView.as_view(), name="versions"),
    path("versions/compare/", VersionCompareView.as_view(), name="version-compare"),
    path("qa/", QuestionListCreateView.as_view(), name="qa"),
    path("qa/<uuid:pk>/", QuestionRetrieveUpdateView.as_view(), name="qa-detail"),
    path("access-logs/", AccessLogListView.as_view(), name="access-logs"),
]
