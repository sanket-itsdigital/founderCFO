import os
from collections import Counter
from datetime import timedelta

from django.db.models import Count, Sum, F
from django.db.models.functions import TruncMonth, TruncDate, ExtractHour
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

        documents = Document.objects.filter(company_id=company_id).select_related(
            "folder"
        )
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
            .exclude(user__isnull=True)
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

        # Document engagement score (top 10 documents by total interactions)
        engagement_qs = (
            documents.annotate(score=F("views_count") + F("downloads_count"))
            .values("id", "name", "folder__name", "score")
            .order_by("-score", "-views_count", "name")[:10]
        )
        engagement_score = [
            {
                "document_id": row["id"],
                "document_name": row["name"],
                "folder_name": row["folder__name"],
                "score": row["score"],
            }
            for row in engagement_qs
        ]

        # Upload trend for last 30 days (daily)
        upload_trend_qs = (
            documents.filter(created_at__gte=last_30)
            .annotate(day=TruncDate("created_at"))
            .values("day")
            .annotate(count=Count("id"))
        )
        upload_trend_map = {
            row["day"].strftime("%Y-%m-%d"): row["count"]
            for row in upload_trend_qs
            if row["day"]
        }
        today_date = timezone.now().date()
        upload_trend = []
        for offset in range(29, -1, -1):
            day = today_date - timedelta(days=offset)
            key = day.strftime("%Y-%m-%d")
            upload_trend.append({"date": key, "count": upload_trend_map.get(key, 0)})

        # User activity heatmap by hour (0-23) for last 30 days
        activity_qs = (
            AccessLog.objects.filter(company_id=company_id, timestamp__gte=last_30)
            .annotate(hour=ExtractHour("timestamp"))
            .values("hour")
            .annotate(count=Count("id"))
        )
        activity_map = {
            int(row["hour"]): row["count"]
            for row in activity_qs
            if row["hour"] is not None
        }
        user_activity_heatmap = [
            {"hour": hour, "count": activity_map.get(hour, 0)} for hour in range(24)
        ]

        # File type distribution
        file_counter = Counter()
        # Use values_list to fetch the file path strings instead of model instances.
        # This avoids combining `only()` (which defers fields) with `select_related()`
        # (which traverses related fields) causing FieldError.
        for file_path in documents.values_list("file", flat=True):
            if not file_path:
                ext = "unknown"
            else:
                ext = os.path.splitext(file_path)[1].lower().lstrip(".") or "unknown"
            file_counter[ext] += 1
        file_type_distribution = [
            {
                "type": ext,
                "count": count,
                "percentage": (
                    round((count / total_documents) * 100, 2)
                    if total_documents
                    else 0.0
                ),
            }
            for ext, count in file_counter.most_common()
        ]

        # Monthly uploads (existing analytics)
        uploads_last_30 = (
            documents.filter(created_at__gte=last_30)
            .annotate(ym=TruncMonth("created_at"))
            .values("ym")
            .annotate(count=Count("id"))
            .order_by("ym")
        )

        analytics = {
            "uploads_over_time": [
                {
                    "month": row["ym"].strftime("%Y-%m") if row["ym"] else None,
                    "count": row["count"],
                }
                for row in uploads_last_30
            ],
            "document_engagement_score": engagement_score,
            "upload_trend_30_days": upload_trend,
            "user_activity_heatmap": user_activity_heatmap,
            "file_type_distribution": file_type_distribution,
        }

        data = {
            "total_documents": total_documents,
            "total_storage_bytes": int(total_storage_bytes),
            "total_storage_mb": (
                round(total_storage_bytes / (1024 * 1024), 2)
                if total_storage_bytes
                else 0.0
            ),
            "total_storage_gb": (
                round(total_storage_bytes / (1024 * 1024 * 1024), 2)
                if total_storage_bytes
                else 0.0
            ),
            "total_views": total_views,
            "downloads": downloads,
            "active_users": active_users,
            "avg_response_time_hours": avg_response,
            "analytics": analytics,
        }
        return Response(data)
