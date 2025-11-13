
from django.conf import settings
from django.shortcuts import get_object_or_404
import jwt
from rest_framework.serializers import ValidationError
from accounts.models import User


def token_validation(token):
    """
    Validate the given JWT token.

    Args:
        token (str): The JWT token to validate.

    Returns:
        User: The user associated with the token if valid.

    Raises:
        ValidationError: If the token is expired or invalid.
    """
    try:
        # Decode the JWT token
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])

        # Extract email and user ID from the payload
        email, user_id = payload.get("email"), payload.get("user_id")

        # Check if email or user ID is provided
        if not email:
            # If email is not provided, use user ID to get the user object
            user = get_object_or_404(User, pk=user_id)
        else:
            # If email is provided, use email to get the user object
            user = get_object_or_404(User, email=email)

        return user
    except jwt.ExpiredSignatureError:
        # Raise validation error if token is expired
        raise ValidationError({"message": "Reset password URL is expired"})
    except jwt.exceptions.DecodeError:
        # Raise validation error if token is invalid
        raise ValidationError({"message": "Invalid Reset password URL"})
