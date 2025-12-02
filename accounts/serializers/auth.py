from rest_framework import serializers
from rest_framework.serializers import ModelSerializer
from django.contrib.auth.password_validation import validate_password
from accounts.models import User
from django.contrib.auth.hashers import make_password
from rest_framework.fields import CharField
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.serializers import ValidationError
from rest_framework.serializers import Serializer
from rest_framework.fields import EmailField


class RegisterUserSerializer(ModelSerializer):

    password = CharField(write_only=True, validators=[validate_password])

    class Meta:
        model = User
        fields = [
            "first_name",
            "middle_name",
            "last_name",
            "email",
            "mobile_number",
            "role",
            "profile_image",
            "password",
            "status",
        ]

    def create(self, validated_data):
        """
        Create a new user instance with hashed password.
        """
        # Hash the password before saving it
        validated_data["password"] = make_password(validated_data["password"])

        # Create user instance with validated data
        return super().create(validated_data)


class LogoutSerializer(Serializer):
    """
    Serializer for logging out a user by invalidating the refresh token.
    """

    refresh = CharField()

    def validate(self, attrs):
        """
        Validate the refresh token.
        """
        refresh_token = attrs.get("refresh")
        try:
            # Attempt to create a RefreshToken instance
            token = RefreshToken(refresh_token)
            # Blacklist (invalidate) the refresh token
            token.blacklist()
            return attrs
        except Exception as e:
            # If there's an error, raise a validation error
            raise ValidationError(str(e))


class ChangePasswordSerializer(Serializer):
    """
    Serializer for validating and handling user password change.
    """

    password = CharField(write_only=True, required=True, validators=[validate_password])
    confirm_password = CharField(write_only=True, required=True)
    old_password = CharField(write_only=True, required=True)

    def validate(self, attrs):
        """
        Validate that the new password and confirm password match.
        """
        if attrs["old_password"] == attrs["password"]:
            raise ValidationError("New password cannot be the same as old password")

        if attrs["password"] != attrs["confirm_password"]:
            raise ValidationError("The new password and confirm password do not match.")
        return attrs

    def validate_old_password(self, value):
        """
        Validate that the old password provided is correct.
        """
        user = self.context["request"].user
        if not user.check_password(value):
            raise ValidationError("Old password is not correct")
        return value

    def save(self):
        """
        Save the new password for the user.
        """
        user = self.context["request"].user
        password = self.validated_data["password"]
        user.set_password(password)
        user.save()
        return user


class ForgotPasswordSerializer(Serializer):
    """
    Serializer for validating and parsing data for forgot password request.
    """

    email = EmailField()


class ResetPasswordSerializer(Serializer):
    """
    Serializer for validating and handling user password change.
    """

    password = CharField(write_only=True, required=True, validators=[validate_password])


class UserProfileSerializer(ModelSerializer):
    """Serializer for exposing user profile data in API responses."""

    full_name = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = User
        fields = [
            "id",
            "first_name",
            "middle_name",
            "last_name",
            "full_name",
            "email",
            "mobile_number",
            "profile_image",
            "role",
            "status",
            "created_at",
        ]
        read_only_fields = ["id", "email", "role", "status", "created_at", "full_name"]

    def get_full_name(self, obj):
        return obj.full_name

    def update(self, instance, validated_data):
        profile_image = validated_data.pop("profile_image", serializers.empty)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        if profile_image is not serializers.empty:
            if profile_image is None:
                instance.profile_image = None
            else:
                instance.profile_image = profile_image

        instance.save()
        return instance


class UserProfileListSerializer(ModelSerializer):
    """Serializer for listing user profile data in API responses."""

    class Meta:
        model = User
        fields = [
            "id",
            "first_name",
            "last_name",
            "email",
            "role",
            "status",
            "profile_image",
        ]
        read_only_fields = ["id", "email", "role", "status", "profile_image"]


class ChangePasswordSerializer(Serializer):

    password = CharField(write_only=True, required=True, validators=[validate_password])
    confirm_password = CharField(write_only=True, required=True)
    old_password = CharField(write_only=True, required=True)

    def validate(self, attrs):

        if attrs["old_password"] == attrs["password"]:
            raise ValidationError(
                "New password cannot be the same as the old password."
            )

        if attrs["password"] != attrs["confirm_password"]:
            raise ValidationError("The passwords do not match. Please try again.")

        return attrs

    def validate_old_password(self, value):
        user = self.context["request"].user
        if not user.check_password(value):
            raise ValidationError("Old password is incorrect.")
        return value

    def save(self):
        """
        Save the new password for the user.
        """
        user = self.context["request"].user
        password = self.validated_data["password"]
        user.set_password(password)
        user.save()
        return user
