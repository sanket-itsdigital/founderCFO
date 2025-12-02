from django import template
from dataroom.models import CompanyFolderSelection, CompanyCategorySelection

register = template.Library()


@register.simple_tag(takes_context=True)
def has_folder_selection(context):
    request = context["request"]
    if not request.user.is_authenticated:
        return False
    user_companies = getattr(request.user, "companies", None)
    if user_companies and user_companies.exists():
        company = request.user.companies.first()
        return CompanyFolderSelection.objects.filter(company=company).exists()
    return False


@register.simple_tag(takes_context=True)
def has_category_selection(context):
    request = context["request"]
    if not request.user.is_authenticated:
        return False
    user_companies = getattr(request.user, "companies", None)
    if user_companies and user_companies.exists():
        company = request.user.companies.first()
        return CompanyCategorySelection.objects.filter(company=company).exists()
    return False
