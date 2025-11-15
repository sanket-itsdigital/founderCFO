from rest_framework import serializers

from accounts.models import Company
from accounts.serializers.auth import UserProfileListSerializer, UserProfileSerializer


class CompanySerializer(serializers.ModelSerializer):
    """Serializer for creating a Company linked to the request user as owner."""

    owner = UserProfileListSerializer(read_only=True)

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
        # owner should be provided by the view via serializer.save(owner=...)
        # If owner is already in validated_data (from view's save call), use it
        # Otherwise, try to get from request context as fallback
        owner = validated_data.pop("owner", None)

        if owner is None:
            request = self.context.get("request")
            if request is None or not hasattr(request, "user"):
                raise serializers.ValidationError(
                    "Request user is required to create a company."
                )
            owner = request.user

        return Company.objects.create(owner=owner, **validated_data)
