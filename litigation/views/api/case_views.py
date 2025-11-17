from django.db.models import Q
from rest_framework import generics
from rest_framework.permissions import IsAuthenticated

from backend.enums import CaseTypeChoices
from litigation.models import Case
from litigation.serializers import CaseSerializer, CaseListSerializer


class CompanyCasesQuerysetMixin:
    def get_queryset(self):
        qs = Case.objects.filter(company__owner=self.request.user)
        company_id = self.request.query_params.get("company_id")
        if company_id:
            qs = qs.filter(company_id=company_id)

        # optional filters: status, risk, search
        status_val = self.request.query_params.get("status")
        risk_val = self.request.query_params.get("risk")
        search = self.request.query_params.get("search")
        if status_val:
            qs = qs.filter(status=status_val)
        if risk_val:
            qs = qs.filter(risk=risk_val)
        if search:
            qs = qs.filter(
                Q(case_number__icontains=search) | Q(synopsis__icontains=search)
            )
        return qs.order_by("-issue_date", "-created_at")


class AllCasesListView(CompanyCasesQuerysetMixin, generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = CaseSerializer

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user, updated_by=self.request.user)

    def get_serializer_class(self):
        if self.request.method.lower() == "get":
            return CaseListSerializer
        return CaseSerializer


class GSTCasesListView(AllCasesListView):
    def get_queryset(self):
        return super().get_queryset().filter(type=CaseTypeChoices.GST)


class IncomeTaxCasesListView(AllCasesListView):
    def get_queryset(self):
        return super().get_queryset().filter(type=CaseTypeChoices.INCOME_TAX)


class LabourPFCasesListView(AllCasesListView):
    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .filter(
                type__in=[
                    CaseTypeChoices.LABOUR,
                    CaseTypeChoices.ESI,
                    CaseTypeChoices.PF,
                ]
            )
        )


class CaseDetailView(CompanyCasesQuerysetMixin, generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = CaseSerializer

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)
