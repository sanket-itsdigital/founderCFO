from rest_framework import serializers

from accounts.models import Company, TeamMember
from litigation.models import Case


class CaseListSerializer(serializers.ModelSerializer):
    company_id = serializers.UUIDField(source="company.id", read_only=True)

    class Meta:
        model = Case
        fields = (
            "id",
            "company_id",
            "case_number",
            "type",
            "synopsis",
            "total_exposure",
            "issue_date",
            "due_date",
            "status",
            "risk",
        )


class CaseSerializer(serializers.ModelSerializer):
    company_id = serializers.UUIDField(write_only=True, required=False)

    class Meta:
        model = Case
        fields = (
            "id",
            "company_id",
            "case_number",
            "category",
            "act_section",
            "authority",
            "type",
            "synopsis",
            "demand_amount",
            "interest_amount",
            "penalty_amount",
            "provision_amount",
            "total_exposure",
            "issue_date",
            "service_date",
            "due_date",
            "hearing_date",
            "final_date",
            "status",
            "risk",
            "likelihood_of_success",
            "internal_responsible_person",
            "designation",
            "responsible_email",
            "consultant_name",
            "consultant_firm",
            "consultant_contact",
            "notes",
            "resolution_details",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at", "total_exposure")
        extra_kwargs = {
            "category": {"required": True, "allow_blank": False},
            "act_section": {"required": True, "allow_blank": False},
            "authority": {"required": True, "allow_blank": False},
            "synopsis": {"required": True, "allow_blank": False},
            "demand_amount": {"required": True},
            "issue_date": {"required": True},
            "status": {"required": True},
            "risk": {"required": True},
            "likelihood_of_success": {"required": True},
        }

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["company_id"] = str(instance.company_id)
        return data

    def validate_company_id(self, value):
        if not value and self.instance:
            # Ignore on updates where company is immutable
            return value
        request = self.context.get("request")
        if not request:
            return value

        # First, get the company by ID
        try:
            company = Company.objects.get(id=value)
        except Company.DoesNotExist:
            raise serializers.ValidationError(
                "The company you selected does not exist. Please select a valid company."
            )

        # Check if user is owner OR active team member of the company
        is_owner = company.owner == request.user
        is_team_member = TeamMember.objects.filter(
            company=company, user=request.user, is_active=True
        ).exists()

        if not (is_owner or is_team_member):
            raise serializers.ValidationError(
                f"You don't have permission to create cases for '{company.name}'. "
                "You must be the company owner or an active team member to perform this action."
            )

        self._validated_company = company
        return value

    def create(self, validated_data):
        company_id = validated_data.pop("company_id", None)
        company = getattr(self, "_validated_company", None)
        if company_id and not company:
            # Check if user is owner OR active team member
            request = self.context.get("request")
            if request:
                try:
                    company = Company.objects.get(id=company_id)
                    # Verify user has access
                    is_owner = company.owner == request.user
                    is_team_member = TeamMember.objects.filter(
                        company=company, user=request.user, is_active=True
                    ).exists()
                    if not (is_owner or is_team_member):
                        raise serializers.ValidationError(
                            {
                                "company_id": (
                                    f"You don't have permission to create cases for '{company.name}'. "
                                    "You must be the company owner or an active team member to perform this action."
                                )
                            }
                        )
                except Company.DoesNotExist:
                    raise serializers.ValidationError(
                        {
                            "company_id": (
                                "The company you selected does not exist. "
                                "Please select a valid company."
                            )
                        }
                    )
        if not company:
            raise serializers.ValidationError(
                {
                    "company_id": (
                        "Company is required. Please provide a valid company ID "
                        "for a company you own or are a team member of."
                    )
                }
            )
        return Case.objects.create(company=company, **validated_data)

    def update(self, instance, validated_data):
        validated_data.pop("company_id", None)
        return super().update(instance, validated_data)
