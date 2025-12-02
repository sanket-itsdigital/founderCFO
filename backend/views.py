from django.shortcuts import render, redirect

from django.contrib.auth.decorators import login_required


from django.db.models import Sum


# @login_required(login_url="login_admin")
def dashboard(request):

    # if request.user.is_superuser:
    # total_order = Order.objects.count()
    # total_brand = Brand.objects.count()
    # total_amount = Order.objects.aggregate(total=Sum("total_amount"))["total"]
    # total_users = User.objects.filter(is_active=True).count()
    # total_product = Product.objects.count()
    # total_vendor_store = VendorBusiness.objects.count()

    bookings_count = 2
    hotels_count = 3
    city_count = 1
    total_collection = 3

    result = 4

    monthly_data = 5
    months = 0
    bookings = 7

    bookings_count = 7

    # Redirect founders without selections to the selection flow
    try:
        user = getattr(request, "user", None)
        if user and user.is_authenticated:
            from backend.enums import UserRoleChoices

            if getattr(user, "role", None) == UserRoleChoices.FOUNDER:
                company = user.companies.first() if hasattr(user, "companies") else None
                if company:
                    from dataroom.models import CompanyFolderSelection

                    if not CompanyFolderSelection.objects.filter(
                        company=company
                    ).exists():
                        return redirect("dataroom:select_folders")
    except Exception:
        # Fail silently; dashboard will render
        pass

    context = {
        # "total_order": total_order,
        # "total_brand": total_brand,
        # "total_amount": total_amount,
        # "total_users": total_users,
        # "total_product": total_product,
        # "total_vendor_store": total_vendor_store,
        "bookings_count": bookings_count,
        "hotels_count": hotels_count,
        "city_count": city_count,
        "total_collection": round(total_collection),
        "result": result,
        "months": months,
        "bookings": bookings,
    }

    return render(request, "adminDashboard.html", context)
