from django.db import models

from backend.models import BaseModel


class Category(BaseModel):
    """HR Budget Category model"""

    name = models.CharField(max_length=255, unique=True)
    description = models.TextField(blank=True)

    class Meta:
        db_table = "hr_budget_category"
        verbose_name = "Budget Category"
        verbose_name_plural = "Budget Categories"
        ordering = ["name"]

    def __str__(self):
        return self.name
