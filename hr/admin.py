from django.contrib import admin

from hr.models import Department, Headcount, Role

# Register your models here.


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "company", "is_active", "created_at")
    search_fields = ("name", "company__name", "description")
    list_filter = ("is_active", "company")
    ordering = ("-created_at",)


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "company", "is_active", "created_at")
    search_fields = ("name", "company__name", "description")
    list_filter = ("is_active", "company")
    ordering = ("-created_at",)


@admin.register(Headcount)
class HeadcountAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "name",
        "email",
        "company",
        "department",
        "role",
        "level",
        "status",
        "employment",
        "start_date",
    )
    search_fields = ("name", "email", "company__name", "department__name", "role__name")
    list_filter = (
        "status",
        "employment",
        "gender",
        "level",
        "company",
        "department",
        "role",
    )
    ordering = ("-created_at",)
    readonly_fields = ("created_at", "updated_at", "created_by", "updated_by")
