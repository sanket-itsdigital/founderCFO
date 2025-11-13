from rest_framework import serializers

from accounts.models import Company


class CompanySerializer(serializers.ModelSerializer):
    """Serializer for creating a Company linked to the request user as owner."""

    class Meta:
        model = Company
        fields = (
            "id",
            "name",
            "GST_number",
            "address",
            "no_of_employees",
            "nature_of_business",
            "owner",
        )
        read_only_fields = ("id", "owner")

    def create(self, validated_data):
        # owner should be provided by the view via context/request
        request = self.context.get("request")
        if request is None or not hasattr(request, "user"):
            raise serializers.ValidationError(
                "Request user is required to create a company."
            )

        owner = request.user
        return Company.objects.create(owner=owner, **validated_data)
