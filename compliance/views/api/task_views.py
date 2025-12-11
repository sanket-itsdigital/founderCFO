from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from compliance.models import ComplianceTaskMaster
from compliance.serializers import (
    ComplianceTaskMasterSerializer,
    ComplianceTaskDropdownSerializer,
)
from accounts.utils import get_user_company
from accounts.models import Company


def get_company_from_request(request):
    """
    Helper function to get company from request with multiple fallback strategies.
    1. Try request.company (set by middleware)
    2. Try get_user_company(request.user)
    3. Try to get from token's company_id (if available)
    """
    # First try: request.company (set by middleware)
    company = getattr(request, "company", None)
    if company:
        return company

    # Second try: get from user
    if request.user.is_authenticated:
        company = get_user_company(request.user)
        if company:
            return company

        # Third try: get from token payload if available
        if hasattr(request, "auth") and request.auth:
            try:
                # Try to get company_id from token payload
                company_id = request.auth.payload.get("company_id")
                if company_id:
                    try:
                        return Company.objects.get(id=company_id)
                    except Company.DoesNotExist:
                        pass
            except (AttributeError, KeyError):
                pass

    return None


class ComplianceTaskListCreateView(generics.ListCreateAPIView):
    """
    List all compliance tasks or create a new one.

    Query Parameters:
    - admin_tasks=true: Show only admin-created tasks (still filtered by company)
    - is_admin_created=true/false: Filter by admin-created status
    - act: Filter by act name
    - status: Filter by status
    - is_overdue: Filter by overdue status (true/false)

    Behavior:
    - For regular users: Always shows tasks selected by their company.
    - For superusers: By default, shows all tasks (for admin management).
    - When admin_tasks=true: Shows only admin-created tasks that are selected by the company.

    Note: For a dedicated endpoint to get only selected tasks, use GET /api/compliance/tasks/selected/
    """

    queryset = ComplianceTaskMaster.objects.all()
    serializer_class = ComplianceTaskMasterSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        queryset = ComplianceTaskMaster.objects.all()

        # Get current company for filtering
        company = get_company_from_request(self.request)

        # For non-superusers, always filter by company's selected tasks
        if not self.request.user.is_superuser:
            if company:
                queryset = queryset.filter(companies=company)
            else:
                # If no company, return empty queryset
                queryset = queryset.none()

        # Check if user wants to see only admin-created tasks (still filtered by company)
        admin_tasks_only = self.request.query_params.get("admin_tasks", None)
        if admin_tasks_only and admin_tasks_only.lower() == "true":
            queryset = queryset.filter(is_admin_created=True)

        # Filter by act if provided
        act = self.request.query_params.get("act", None)
        if act:
            queryset = queryset.filter(act=act)

        # Filter by status if provided
        status = self.request.query_params.get("status", None)
        if status:
            queryset = queryset.filter(status=status)

        # Filter by is_overdue if provided
        is_overdue = self.request.query_params.get("is_overdue", None)
        if is_overdue is not None:
            queryset = queryset.filter(is_overdue=is_overdue.lower() == "true")

        # Filter by is_admin_created if provided
        is_admin_created = self.request.query_params.get("is_admin_created", None)
        if is_admin_created is not None:
            queryset = queryset.filter(
                is_admin_created=is_admin_created.lower() == "true"
            )

        return queryset.order_by("-created_at")

    def perform_create(self, serializer):
        # Save the task instance
        task = serializer.save(
            created_by=self.request.user, updated_by=self.request.user
        )

        # Get company from request and add it to the task's companies
        company = get_company_from_request(self.request)
        if company:
            task.companies.add(company)


class ComplianceTaskRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    """
    Retrieve, update or delete a compliance task.
    For regular users: Only allows access to tasks selected by their company.
    For superusers: Allows access to all tasks.
    """

    queryset = ComplianceTaskMaster.objects.all()
    serializer_class = ComplianceTaskMasterSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        queryset = ComplianceTaskMaster.objects.all()

        # For non-superusers, filter by company's selected tasks
        if not self.request.user.is_superuser:
            company = get_company_from_request(self.request)
            if company:
                queryset = queryset.filter(companies=company)
            else:
                queryset = queryset.none()

        return queryset

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)


class ComplianceTaskSelectionView(APIView):
    """
    API endpoint for companies to select or deselect compliance tasks.
    GET /api/compliance/tasks/select/ - List all available tasks (admin-created) for selection
    POST /api/compliance/tasks/select/ - Select tasks for the company
    DELETE /api/compliance/tasks/select/ - Deselect tasks for the company
    """

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        """
        Select tasks for the company.
        Expects: {"task_ids": [uuid1, uuid2, ...]}
        """
        company = get_company_from_request(request)
        if not company:
            return Response(
                {"detail": "No company associated with this user."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        task_ids = request.data.get("task_ids", [])
        if not isinstance(task_ids, list):
            return Response(
                {"detail": "task_ids must be a list."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Get tasks that exist and are admin-created
        tasks = ComplianceTaskMaster.objects.filter(
            id__in=task_ids, is_admin_created=True
        )

        if tasks.count() != len(task_ids):
            return Response(
                {"detail": "Some task IDs are invalid or not admin-created."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Add company to selected tasks
        company.selected_compliance_tasks.add(*tasks)

        return Response(
            {
                "detail": f"Successfully selected {tasks.count()} task(s).",
                "selected_tasks": [
                    {"id": str(task.id), "task_id": task.task_id, "act": task.act}
                    for task in tasks
                ],
            },
            status=status.HTTP_200_OK,
        )

    def delete(self, request):
        """
        Deselect tasks for the company.
        Expects: {"task_ids": [uuid1, uuid2, ...]}
        """
        company = get_company_from_request(request)
        if not company:
            return Response(
                {"detail": "No company associated with this user."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        task_ids = request.data.get("task_ids", [])
        if not isinstance(task_ids, list):
            return Response(
                {"detail": "task_ids must be a list."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Get tasks that are currently selected by the company
        tasks = company.selected_compliance_tasks.filter(id__in=task_ids)

        if not tasks.exists():
            return Response(
                {"detail": "No matching selected tasks found."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Remove company from selected tasks
        company.selected_compliance_tasks.remove(*tasks)

        return Response(
            {
                "detail": f"Successfully deselected {tasks.count()} task(s).",
                "deselected_tasks": [
                    {"id": str(task.id), "task_id": task.task_id, "act": task.act}
                    for task in tasks
                ],
            },
            status=status.HTTP_200_OK,
        )


class ComplianceTaskDropdownView(APIView):
    """
    API endpoint to get admin tasks for dropdown selection.
    Returns only id and name (task_id - particulars) for admin-created tasks.
    GET /api/compliance/tasks/dropdown/
    """

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        """Return all admin-created tasks with only id and name for dropdown."""
        # Get all admin-created tasks
        admin_tasks = ComplianceTaskMaster.objects.filter(
            is_admin_created=True
        ).order_by("act", "task_id")

        serializer = ComplianceTaskDropdownSerializer(admin_tasks, many=True)
        return Response(serializer.data)


class ComplianceTaskSelectedView(generics.ListAPIView):
    """
    API endpoint to get tasks selected by the company.
    GET /api/compliance/tasks/selected/

    Query Parameters:
    - act: Filter by act name
    - status: Filter by status
    - is_overdue: Filter by overdue status (true/false)

    Returns only tasks that the company has selected from admin-created tasks.
    """

    serializer_class = ComplianceTaskMasterSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """Return tasks selected by the company."""
        company = get_company_from_request(self.request)
        if not company:
            return ComplianceTaskMaster.objects.none()

        # Get tasks selected by the company
        queryset = company.selected_compliance_tasks.all()

        # Filter by act if provided
        act = self.request.query_params.get("act", None)
        if act:
            queryset = queryset.filter(act=act)

        # Filter by status if provided
        status = self.request.query_params.get("status", None)
        if status:
            queryset = queryset.filter(status=status)

        # Filter by is_overdue if provided
        is_overdue = self.request.query_params.get("is_overdue", None)
        if is_overdue is not None:
            queryset = queryset.filter(is_overdue=is_overdue.lower() == "true")

        return queryset.order_by("-created_at")
