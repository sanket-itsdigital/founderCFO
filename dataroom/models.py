from django.conf import settings
from django.db import models
from django.utils import timezone

from backend.models import BaseModel


class Folder(BaseModel):
    company = models.ForeignKey(
        "accounts.Company", on_delete=models.CASCADE, related_name="folders"
    )
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = ("company", "name")
        ordering = ["name"]

    def __str__(self) -> str:
        return f"{self.company.name} / {self.name}"


class Document(BaseModel):
    company = models.ForeignKey(
        "accounts.Company", on_delete=models.CASCADE, related_name="documents"
    )
    folder = models.ForeignKey(
        Folder, on_delete=models.PROTECT, related_name="documents"
    )
    name = models.CharField(max_length=255)
    file = models.FileField(upload_to="dataroom/docs/%Y/%m/")
    size_bytes = models.BigIntegerField(default=0)
    access_notes = models.CharField(max_length=255, blank=True)
    views_count = models.PositiveIntegerField(default=0)
    downloads_count = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["company", "folder"]),
            models.Index(fields=["name"]),
        ]

    def __str__(self) -> str:
        return self.name


class DocumentVersion(BaseModel):
    document = models.ForeignKey(
        Document, on_delete=models.CASCADE, related_name="versions"
    )
    version_no = models.PositiveIntegerField()
    file = models.FileField(upload_to="dataroom/versions/%Y/%m/")
    size_bytes = models.BigIntegerField(default=0)

    class Meta:
        unique_together = ("document", "version_no")
        ordering = ["-created_at"]


class Question(BaseModel):
    document = models.ForeignKey(
        Document, on_delete=models.CASCADE, related_name="questions"
    )
    asked_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="asked_questions",
    )
    question = models.TextField()
    answer_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="answered_questions",
    )
    answer = models.TextField(blank=True)
    is_answered = models.BooleanField(default=False)

    class Meta:
        ordering = ["-created_at"]


class AccessLog(BaseModel):
    VIEW = "view"
    DOWNLOAD = "download"
    ACTION_CHOICES = ((VIEW, "view"), (DOWNLOAD, "download"))

    company = models.ForeignKey(
        "accounts.Company", on_delete=models.CASCADE, related_name="access_logs"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="dataroom_access_logs",
    )
    document = models.ForeignKey(
        Document,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="access_logs",
    )
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    timestamp = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-timestamp"]
        indexes = [
            models.Index(fields=["company", "timestamp"]),
            models.Index(fields=["action"]),
        ]
