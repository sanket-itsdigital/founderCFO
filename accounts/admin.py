from django.contrib import admin

from accounts.models import Company, User

# Register your models here.

@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "owner", "GST_number", "no_of_employees")
    search_fields = ("name", "GST_number", "owner__username", "owner__email")
    list_filter = ("no_of_employees",)
    ordering = ("-id",)
    
@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ("id", "email", "first_name", "last_name", "is_active", "is_staff")
    search_fields = ("email", "first_name", "last_name")
    list_filter = ("is_active", "is_staff", "role", "status")
    ordering = ("-id",)