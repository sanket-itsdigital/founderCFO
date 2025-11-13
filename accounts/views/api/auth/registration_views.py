from rest_framework.response import Response
from rest_framework import status
from rest_framework.generics import CreateAPIView
from rest_framework.permissions import AllowAny
from django.db import transaction
from accounts.serializers import RegisterUserSerializer
from rest_framework.views import APIView
from rest_framework.serializers import ValidationError

from backend.utils import token_validation

class SignupView(CreateAPIView):
    """
    View for user signup.
    """

    permission_classes = [AllowAny]
    serializer_class = RegisterUserSerializer

    def post(self, request):
        """
        Handle user sign-up request.

        Args:
            request: HTTP request object.

        Returns:
            Response indicating success or failure of user sign-up.
        """

        # validate the incoming data
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)

        with transaction.atomic():
            user = serializer.save()
            user.save()

        return Response(
            data={
                "message": "Registration successful. Thank you for joining us.",
            },
            status=status.HTTP_200_OK,
        )


class ValidateTokenAPIView(APIView):
    def get(self, request, *args, **kwargs):
        """
        Validate a JWT token.

        This endpoint is used to validate a JWT token. It checks if the token is valid and returns
        a success message if it is, or an error message if it is not.

        Args:
            request: The HTTP request.
            *args: Additional positional arguments.
            **kwargs: Additional keyword arguments. Expected to contain the token.

        Returns:
            Response: HTTP response indicating success or failure of token validation.

        """
        token = kwargs.get("token")
        try:
            # Call the token_validation function to validate the token
            _ = token_validation(token)
            # Return success response if validation succeeds
            return Response(
                {"message": "Success"},
                status=status.HTTP_200_OK,
            )
        except ValidationError as e:
            # Return error response if validation fails
            return Response(
                {"message": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )
