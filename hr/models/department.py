from backend.models import BaseModel
from django.db import models


class Department(BaseModel):
    company = models.ForeignKey(
        "accounts.Company",
        on_delete=models.CASCADE,
        related_name="departments",
    )
    name = models.CharField(max_length=255)
    description = models.TextField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "department"
        verbose_name = "Department"
        verbose_name_plural = "Departments"
        unique_together = [["company", "name"]]

    def __str__(self):
        return self.name
