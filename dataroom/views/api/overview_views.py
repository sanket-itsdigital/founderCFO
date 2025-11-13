from datetime import timedelta
from django.db.models import Count, Sum
from django.utils import timezone
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from dataroom.models import Document, AccessLog, Question


class OverviewView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        company_id = request.query_params.get("company_id")
        if not company_id:
            return Response({"detail": "company_id is required"}, status=400)

        documents = Document.objects.filter(company_id=company_id)
        total_documents = documents.count()
        total_storage_bytes = (
            documents.aggregate(total=Sum("size_bytes")).get("total") or 0
        )
        total_views = documents.aggregate(total=Sum("views_count")).get("total") or 0
        downloads = documents.aggregate(total=Sum("downloads_count")).get("total") or 0

        # Active users in last 30 days
        last_30 = timezone.now() - timedelta(days=30)
        active_users = (
            AccessLog.objects.filter(company_id=company_id, timestamp__gte=last_30)
            .values("user")
            .distinct()
            .count()
        )

        # Avg response time for Q&A: time to answer from question created to answer updated
        answered = Question.objects.filter(
            document__company_id=company_id, is_answered=True
        )
        total_hours = 0.0
        answered_count = answered.count()
        for q in answered.only("created_at", "updated_at"):
            if q.updated_at and q.created_at:
                total_hours += (q.updated_at - q.created_at).total_seconds() / 3600.0
        avg_response = round(total_hours / answered_count, 2) if answered_count else 0.0

        # Simple analytics examples
        uploads_last_30 = (
            documents.filter(created_at__gte=last_30)
            .extra(select={"ym": "strftime('%Y-%m', created_at)"})
            .values("ym")
            .annotate(count=Count("id"))
        )

        analytics = {
            "uploads_over_time": list(uploads_last_30),
        }

        data = {
            "total_documents": total_documents,
            "total_storage_bytes": (
                total_storage_bytes
                if isinstance(total_storage_bytes, int)
                else (total_storage_bytes or 0)
            ),
            "total_views": total_views,
            "downloads": downloads,
            "active_users": active_users,
            "avg_response_time_hours": avg_response,
            "analytics": analytics,
        }
        return Response(data)
