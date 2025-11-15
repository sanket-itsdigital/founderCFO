from rest_framework import generics, permissions
from compliance.models import ComplianceTaskMaster
from compliance.serializers import ComplianceTaskMasterSerializer


class ComplianceTaskListCreateView(generics.ListCreateAPIView):
    """
    List all compliance tasks or create a new one.
    """
    queryset = ComplianceTaskMaster.objects.all()
    serializer_class = ComplianceTaskMasterSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        queryset = ComplianceTaskMaster.objects.all()
        
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

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user, updated_by=self.request.user)


class ComplianceTaskRetrieveUpdateDestroyView(
    generics.RetrieveUpdateDestroyAPIView
):
    """
    Retrieve, update or delete a compliance task.
    """
    queryset = ComplianceTaskMaster.objects.all()
    serializer_class = ComplianceTaskMasterSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)

