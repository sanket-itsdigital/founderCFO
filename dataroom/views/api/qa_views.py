from rest_framework import generics, permissions
from rest_framework.response import Response

from dataroom.models import Question
from dataroom.serializers import QuestionSerializer


class QuestionListCreateView(generics.ListCreateAPIView):
    serializer_class = QuestionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        document_id = self.request.query_params.get("document_id")
        company_id = self.request.query_params.get("company_id")
        qs = Question.objects.all()
        if document_id:
            qs = qs.filter(document_id=document_id)
        if company_id:
            qs = qs.filter(document__company_id=company_id)
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
