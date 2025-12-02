from rest_framework import generics, permissions

from dataroom.models import AccessLog
from dataroom.serializers import AccessLogSerializer


class AccessLogListView(generics.ListCreateAPIView):
    serializer_class = AccessLogSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        company_id = self.request.query_params.get("company_id")
        action = self.request.query_params.get("action")
        qs = AccessLog.objects.filter(company_id=company_id)
        if action:
            qs = qs.filter(action=action)
        return qs.select_related("user", "document")

    def perform_create(self, serializer):
        serializer.save(
            user=self.request.user,
            company_id=self.request.data.get("company")
            or self.request.query_params.get("company_id"),
        )
