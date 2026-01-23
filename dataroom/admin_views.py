from django.shortcuts import redirect, render
from django.contrib.auth.decorators import login_required

from dataroom.forms import (
    DataRoomForm,
    FileCategoryForm,
    FolderSelectionForm,
    CategorySelectionForm,
    LoginForm,
)
from django.contrib import messages

from dataroom.models import (
    Folder,
    FileCategory,
    CompanyFolderSelection,
    CompanyCategorySelection,
)
from accounts.models import Company, User
from django.contrib.auth import authenticate, login, logout


# Create your views here.


def login_admin(request):

    forms = LoginForm()
    if request.method == "POST":
        forms = LoginForm(request.POST)
        if forms.is_valid():
            email = forms.cleaned_data["email"]
            password = forms.cleaned_data["password"]

            try:
                user = User.objects.get(email=email)
                print("user:", user)
            except User.DoesNotExist:
                return render(
                    request, "adminLogin.html", {"error": "Invalid email or password"}
                )

            if user:
                if user.check_password(password):
                    print("Authenticated user:", user)
                    if user.is_superuser:
                        login(request, user)
                        return redirect("dashboard")
                    else:
                        messages.error(request, "You are not superuser")
                        context = {"form": forms}
                        return render(request, "adminLogin.html", context)
                else:
                    return render(
                        request,
                        "adminLogin.html",
                        {"error": "Invalid email or password"},
                    )

            else:
                messages.error(request, "wrong username password")
    context = {"form": forms}
    return render(request, "adminLogin.html", context)


def logout_page(request):
    logout(request)
    return redirect("login_admin")

def add_folder(request):

    if request.method == "POST":

        forms = DataRoomForm(request.POST, request.FILES)

        if forms.is_valid():
            # Folder is now global; simply save.
            instance = forms.save()
            return redirect("dataroom:list_folder")
        else:
            print(forms.errors)
            context = {"form": forms}
            return render(request, "add_folder.html", context)

    else:

        return render(request, "add_folder.html", {"form": DataRoomForm()})


def list_folder(request):

    data = Folder.objects.all().order_by("name")

    return render(request, "list_folder.html", {"data": data})


def update_folder(request, folder_id):

    instance = Folder.objects.get(id=folder_id)

    if request.method == "POST":

        forms = DataRoomForm(request.POST, instance=instance)

        if forms.is_valid():
            forms.save()
            return redirect("dataroom:list_folder")
        else:
            print(forms.errors)
            context = {"form": forms}
            return render(request, "add_folder.html", context)

    else:

        # create first row using admin then editing only

        forms = DataRoomForm(instance=instance)

        context = {"form": forms}

        return render(request, "add_folder.html", context)


def delete_folder(request, folder_id):

    data = Folder.objects.get(id=folder_id).delete()

    return redirect("dataroom:list_folder")


# -------- Category management (Superadmin) --------


def add_category(request):

    if request.method == "POST":
        form = FileCategoryForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect("dataroom:list_category")
        return render(request, "add_category.html", {"form": form})
    else:
        return render(request, "add_category.html", {"form": FileCategoryForm()})


def list_category(request):
    data = FileCategory.objects.select_related("folder").order_by(
        "folder__name", "name"
    )
    return render(request, "list_category.html", {"data": data})


def update_category(request, category_id):
    instance = FileCategory.objects.get(id=category_id)
    if request.method == "POST":
        form = FileCategoryForm(request.POST, instance=instance)
        if form.is_valid():
            form.save()
            return redirect("dataroom:list_category")
        return render(request, "add_category.html", {"form": form})
    else:
        return render(
            request, "add_category.html", {"form": FileCategoryForm(instance=instance)}
        )


def delete_category(request, category_id):
    FileCategory.objects.filter(id=category_id).delete()
    return redirect("dataroom:list_category")


# -------- Company selection (Founder) --------


def select_folders(request):
    company = None
    if hasattr(request, "user") and request.user.is_authenticated:
        user_companies = getattr(request.user, "companies", None)
        if user_companies and user_companies.exists():
            company = request.user.companies.first()
    if company is None:
        company = Company.objects.first()

    if company is None:
        # No company exists – show message using form non-field errors
        form = FolderSelectionForm()
        form.add_error(None, "No company available.")
        return render(request, "select_folders.html", {"form": form})

    if request.method == "POST":
        form = FolderSelectionForm(request.POST)
        if form.is_valid():
            selected = list(form.cleaned_data.get("folders", []))
            # Sync selections: remove deselected
            CompanyFolderSelection.objects.filter(company=company).exclude(
                folder__in=selected
            ).delete()
            # Add new selections
            existing_ids = set(
                CompanyFolderSelection.objects.filter(company=company).values_list(
                    "folder_id", flat=True
                )
            )
            for folder in selected:
                if folder.id not in existing_ids:
                    CompanyFolderSelection.objects.create(
                        company=company, folder=folder
                    )
            return redirect("dataroom:select_categories")
    else:
        preselected = Folder.objects.filter(company_selections__company=company)
        form = FolderSelectionForm(initial={"folders": preselected})
    return render(request, "select_folders.html", {"form": form, "company": company})


def select_categories(request):
    company = None
    if hasattr(request, "user") and request.user.is_authenticated:
        user_companies = (
            getattr(request, "user").companies
            if hasattr(request.user, "companies")
            else None
        )
        if user_companies and user_companies.exists():
            company = request.user.companies.first()
    if company is None:
        company = Company.objects.first()

    if company is None:
        form = CategorySelectionForm()
        form.add_error(None, "No company available.")
        return render(request, "select_categories.html", {"form": form})

    selected_folders = Folder.objects.filter(company_selections__company=company)
    categories_qs = FileCategory.objects.filter(
        folder__in=selected_folders
    ).select_related("folder")

    if request.method == "POST":
        form = CategorySelectionForm(request.POST)
        form.fields["categories"].queryset = categories_qs
        if form.is_valid():
            selected = list(form.cleaned_data.get("categories", []))
            CompanyCategorySelection.objects.filter(company=company).exclude(
                category__in=selected
            ).delete()
            existing_ids = set(
                CompanyCategorySelection.objects.filter(company=company).values_list(
                    "category_id", flat=True
                )
            )
            for category in selected:
                if category.id not in existing_ids:
                    CompanyCategorySelection.objects.create(
                        company=company, category=category
                    )
            return redirect("dataroom:list_folder")
    else:
        preselected = FileCategory.objects.filter(
            company_selections__company=company, folder__in=selected_folders
        )
        form = CategorySelectionForm(initial={"categories": preselected})
        form.fields["categories"].queryset = categories_qs
    return render(
        request,
        "select_categories.html",
        {"form": form, "company": company, "folders": selected_folders},
    )


@login_required
def user_profile(request):
    return render(request, "profile.html", {"user": request.user})


@login_required
def list_users(request):
    """List all users for admin"""
    from django.core.paginator import Paginator
    from accounts.utils import get_user_company
    
    users = User.objects.all().order_by("-created_at")
    
    # Add contact_phone and company_name property to each user for template compatibility
    for user in users:
        user.contact_phone = user.mobile_number or ""
        user.gender = ""  # Gender field not in model, set empty
        
        # Get company name - check owned companies first, then team memberships
        company = get_user_company(user)
        user.company_name = company.name if company else "-"
    
    # Pagination
    paginator = Paginator(users, 25)  # 25 users per page
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)
    
    context = {
        "data": page_obj,
        "page_obj": page_obj,
    }
    
    return render(request, "custom_user_list.html", context)


@login_required
def list_company_subscriptions(request):
    """List all company subscriptions for admin"""
    from django.core.paginator import Paginator
    from subscriptions.models import CompanySubscription
    
    subscriptions = CompanySubscription.objects.select_related(
        'company', 'plan', 'purchased_by'
    ).all().order_by("-created_at")
    
    # Pagination
    paginator = Paginator(subscriptions, 25)  # 25 subscriptions per page
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)
    
    context = {
        "data": page_obj,
        "page_obj": page_obj,
    }
    
    return render(request, "company_subscription_list.html", context)
