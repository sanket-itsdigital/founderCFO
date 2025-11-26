from rest_framework import generics, permissions
from compliance.models import CompliancePayments
from compliance.serializers import CompliancePaymentSerializer


class CompliancePaymentListCreateView(generics.ListCreateAPIView):
    """
    List all compliance payments or create a new one.
    """

    queryset = CompliancePayments.objects.all()
    serializer_class = CompliancePaymentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        queryset = CompliancePayments.objects.all()

        # For non-superusers, filter by company's selected tasks
        if not self.request.user.is_superuser:
            company = getattr(self.request, "company", None)
            if company:
                # Get task IDs for company's selected tasks
                company_task_ids = company.selected_compliance_tasks.values_list(
                    "id", flat=True
                )
                queryset = queryset.filter(compliance_task_id__in=company_task_ids)
            else:
                queryset = queryset.none()

        # Filter by task_id if provided
        task_id = self.request.query_params.get("task_id", None)
        if task_id:
            queryset = queryset.filter(task_id=task_id)

        # Filter by related_act if provided
        related_act = self.request.query_params.get("related_act", None)
        if related_act:
            queryset = queryset.filter(related_act=related_act)

        # Filter by is_late if provided
        is_late = self.request.query_params.get("is_late", None)
        if is_late is not None:
            queryset = queryset.filter(is_late=is_late.lower() == "true")

        return queryset.order_by("-payment_date", "-created_at")

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user, updated_by=self.request.user)


class CompliancePaymentRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    """
    Retrieve, update or delete a compliance payment.
    For regular users: Only allows access to payments for tasks selected by their company.
    For superusers: Allows access to all payments.
    """

    queryset = CompliancePayments.objects.all()
    serializer_class = CompliancePaymentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        queryset = CompliancePayments.objects.all()

        # For non-superusers, filter by company's selected tasks
        if not self.request.user.is_superuser:
            company = getattr(self.request, "company", None)
            if company:
                # Get task IDs for company's selected tasks
                company_task_ids = company.selected_compliance_tasks.values_list(
                    "id", flat=True
                )
                queryset = queryset.filter(compliance_task_id__in=company_task_ids)
            else:
                queryset = queryset.none()

        return queryset

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)
