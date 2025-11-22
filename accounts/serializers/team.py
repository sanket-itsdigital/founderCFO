from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password

from accounts.models import TeamMember, User
from backend.enums import UserRoleChoices
from accounts.serializers.auth import UserProfileListSerializer


class TeamMemberSerializer(serializers.ModelSerializer):
    """Read-only serializer for exposing team members."""

    user = UserProfileListSerializer(read_only=True)
    invited_by = UserProfileListSerializer(read_only=True)
    company = serializers.CharField(source="company.name", read_only=True)

    class Meta:
        model = TeamMember
        fields = (
            "id",
            "company",
            "role",
            "is_active",
            "user",
            "invited_by",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields


class TeamMemberCreateSerializer(serializers.ModelSerializer):
    """Serializer used when founders add a new team member."""

    # first_name = serializers.CharField(write_only=True, max_length=30)
    # middle_name = serializers.CharField(
    #     write_only=True,
    #     max_length=30,
    #     allow_blank=True,
    #     required=False,
    # )
    # last_name = serializers.CharField(write_only=True, max_length=30)
    email = serializers.EmailField(write_only=True)
    mobile_number = serializers.CharField(
        write_only=True,
        max_length=15,
        allow_blank=True,
        required=False,
    )
    profile_image = serializers.ImageField(
        write_only=True,
        allow_null=True,
        required=False,
    )
    password = serializers.CharField(
        write_only=True,
        required=True,
        style={"input_type": "password"},
    )

    class Meta:
        model = TeamMember
        fields = (
            "id",
            "role",
            # "first_name",
            # "middle_name",
            # "last_name",
            "email",
            "mobile_number",
            "profile_image",
            "password",
        )
        read_only_fields = ("id",)

    def validate_role(self, value):
        if value == UserRoleChoices.FOUNDER:
            raise serializers.ValidationError(
                "Founder role cannot be assigned to a team member."
            )
        return value

    def validate(self, attrs):
        company = self.context.get("company")
        if company is None:
            raise serializers.ValidationError("Company context is required.")

        email = attrs.get("email")
        existing_user = User.objects.filter(email=email).first()
        if (
            existing_user
            and TeamMember.objects.filter(company=company, user=existing_user).exists()
        ):
            raise serializers.ValidationError(
                {"email": "User is already part of the current company."}
            )

        mobile_number = attrs.get("mobile_number")
        if mobile_number:
            mobile_qs = User.objects.filter(mobile_number=mobile_number)
            if existing_user:
                mobile_qs = mobile_qs.exclude(pk=existing_user.pk)
            if mobile_qs.exists():
                raise serializers.ValidationError(
                    {"mobile_number": "This mobile number is already in use."}
                )

        password = attrs.get("password")
        if not password:
            raise serializers.ValidationError({"password": "Password is required."})
        validate_password(password)

        return attrs

    def create(self, validated_data):
        company = self.context.get("company")
        request = self.context.get("request")

        profile_image = validated_data.pop("profile_image", None)
        email = validated_data.pop("email")
        mobile_number = validated_data.pop("mobile_number", None)
        raw_password = validated_data.pop("password")

        user_defaults = {
            # "first_name": validated_data.pop("first_name"),
            # "middle_name": validated_data.pop("middle_name", None),
            # "last_name": validated_data.pop("last_name"),
            "role": validated_data["role"],
        }
        if mobile_number:
            user_defaults["mobile_number"] = mobile_number

        user, created = User.objects.get_or_create(email=email, defaults=user_defaults)

        if not created:
            for field, value in user_defaults.items():
                setattr(user, field, value)
        if raw_password:
            user.set_password(raw_password)
        elif created:
            user.set_unusable_password()

        if profile_image is not None:
            user.profile_image = profile_image

        user.role = validated_data["role"]
        user.save()

        return TeamMember.objects.create(
            company=company,
            user=user,
            role=validated_data["role"],
            invited_by=request.user if request else None,
            created_by=request.user if request else None,
            updated_by=request.user if request else None,
        )


class TeamMemberUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating existing team members."""

    first_name = serializers.CharField(write_only=True, max_length=30, required=False)
    middle_name = serializers.CharField(
        write_only=True,
        max_length=30,
        allow_blank=True,
        required=False,
    )
    last_name = serializers.CharField(write_only=True, max_length=30, required=False)
    mobile_number = serializers.CharField(
        write_only=True,
        max_length=15,
        allow_blank=True,
        required=False,
    )
    profile_image = serializers.ImageField(
        write_only=True,
        allow_null=True,
        required=False,
    )

    class Meta:
        model = TeamMember
        fields = (
            "id",
            "role",
            "is_active",
            "first_name",
            "middle_name",
            "last_name",
            "mobile_number",
            "profile_image",
        )
        read_only_fields = ("id",)

    def validate_role(self, value):
        if value == UserRoleChoices.FOUNDER:
            raise serializers.ValidationError(
                "Founder role cannot be assigned to a team member."
            )
        return value

    def validate(self, attrs):
        team_member = self.instance
        user = team_member.user

        mobile_number = attrs.get("mobile_number")
        if mobile_number:
            mobile_qs = User.objects.filter(mobile_number=mobile_number).exclude(
                pk=user.pk
            )
            if mobile_qs.exists():
                raise serializers.ValidationError(
                    {"mobile_number": "This mobile number is already in use."}
                )

        return attrs

    def update(self, instance, validated_data):
        request = self.context.get("request")
        user = instance.user

        profile_image = validated_data.pop("profile_image", serializers.empty)

        for field in ("first_name", "middle_name", "last_name", "mobile_number"):
            if field in validated_data:
                setattr(user, field, validated_data[field])

        if "role" in validated_data:
            instance.role = validated_data["role"]
            user.role = validated_data["role"]

        if profile_image is not serializers.empty:
            if profile_image is None:
                user.profile_image = None
            else:
                user.profile_image = profile_image

        if "is_active" in validated_data:
            instance.is_active = validated_data["is_active"]

        user.save()

        if request:
            instance.updated_by = request.user
        instance.save()

        return instance
