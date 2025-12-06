from accounts.models import Company


def get_company_from_request(request):
    """Helper function to get company from request"""
    company_id = request.query_params.get("company_id")
    if company_id:
        try:
            return Company.objects.get(id=company_id, owner=request.user)
        except Company.DoesNotExist:
            return None
    # Try to get the first company owned by the user
    return Company.objects.filter(owner=request.user).first()

