from rest_framework import generics, permissions
from rest_framework.response import Response

from accounts.utils import get_user_company
from dataroom.models import Question
from dataroom.serializers import QuestionSerializer


class QuestionListCreateView(generics.ListCreateAPIView):
    serializer_class = QuestionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """Restrict Q&A to the current user's company."""
        document_id = self.request.query_params.get("document_id")
        user_company = get_user_company(self.request.user)

        # If user has no company, return empty queryset
        if not user_company:
            return Question.objects.none()

        qs = Question.objects.filter(document__company=user_company)
        if document_id:
            qs = qs.filter(document_id=document_id)

        return qs.select_related("asked_by", "answer_by")

    def perform_create(self, serializer):
        serializer.save(
            asked_by=self.request.user,
            created_by=self.request.user,
            updated_by=self.request.user,
        )


class QuestionRetrieveUpdateView(generics.RetrieveUpdateAPIView):
    queryset = Question.objects.all()
    serializer_class = QuestionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_update(self, serializer):
        # If answer is being provided, set flags
        instance = serializer.save(updated_by=self.request.user)
        if instance.answer and not instance.is_answered:
            instance.is_answered = True
            instance.answer_by = self.request.user
            instance.save(
                update_fields=["is_answered", "answer_by", "updated_at", "updated_by"]
            )
        return instance
