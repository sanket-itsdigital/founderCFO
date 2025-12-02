from django.urls import path

from dataroom.admin_views import (
    add_folder,
    delete_folder,
    list_folder,
    update_folder,
    add_category,
    list_category,
    update_category,
    delete_category,
    select_folders,
    select_categories,
)
from dataroom.views.api.overview_views import OverviewView
from dataroom.views.api.folder_views import (
    FolderListCreateView,
    FolderRetrieveUpdateView,
)
from dataroom.views.api.document_views import (
    DocumentListCreateView,
    DocumentRetrieveUpdateView,
    DocumentDownloadView,
    FolderDocumentsView,
    DocumentVersionListCreateView,
    VersionCompareView,
    CurrentCompanyDocumentListView,
)
from dataroom.views.api.qa_views import (
    QuestionListCreateView,
    QuestionRetrieveUpdateView,
)
from dataroom.views.api.access_log_views import AccessLogListView
from dataroom.views.api.company import (
    AvailableFoldersListView,
    CompanyFolderSelectionView,
    CompanySelectedFoldersListView,
    AvailableCategoriesListView,
    CompanyCategorySelectionView,
    CompanySelectedCategoriesListView,
)

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
        "documents/current-company/",
        CurrentCompanyDocumentListView.as_view(),
        name="documents-current-company",
    ),
    path(
        "documents/<uuid:pk>/",
        DocumentRetrieveUpdateView.as_view(),
        name="document-detail",
    ),
    path(
        "documents/<uuid:pk>/download/",
        DocumentDownloadView.as_view(),
        name="document-download",
    ),
    path("versions/", DocumentVersionListCreateView.as_view(), name="versions"),
    path("versions/compare/", VersionCompareView.as_view(), name="version-compare"),
    path("qa/", QuestionListCreateView.as_view(), name="qa"),
    path("qa/<uuid:pk>/", QuestionRetrieveUpdateView.as_view(), name="qa-detail"),
    path("access-logs/", AccessLogListView.as_view(), name="access-logs"),
    # Company Folder Selection APIs
    path(
        "company/folders/available/",
        AvailableFoldersListView.as_view(),
        name="available-folders",
    ),
    path(
        "company/folders/select/",
        CompanyFolderSelectionView.as_view(),
        name="select-folders",
    ),
    path(
        "company/folders/selected/",
        CompanySelectedFoldersListView.as_view(),
        name="selected-folders",
    ),
    # Company Category Selection APIs
    path(
        "company/categories/available/",
        AvailableCategoriesListView.as_view(),
        name="available-categories",
    ),
    path(
        "company/categories/select/",
        CompanyCategorySelectionView.as_view(),
        name="select-categories",
    ),
    path(
        "company/categories/selected/",
        CompanySelectedCategoriesListView.as_view(),
        name="selected-categories",
    ),
    # Admin Views
    path("add-folder/", add_folder, name="add_folder"),
    path("list-folder/", list_folder, name="list_folder"),
    path("update-folder/<folder_id>", update_folder, name="update_folder"),
    path("delete-folder/<folder_id>", delete_folder, name="delete_folder"),
    # Category management (superadmin)
    path("add-category/", add_category, name="add_category"),
    path("list-category/", list_category, name="list_category"),
    path("update-category/<category_id>", update_category, name="update_category"),
    path("delete-category/<category_id>", delete_category, name="delete_category"),
    # Founder selection
    path("select-folders/", select_folders, name="select_folders"),
    path("select-categories/", select_categories, name="select_categories"),
]
