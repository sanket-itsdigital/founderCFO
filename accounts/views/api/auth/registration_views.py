from django.db import transaction
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.generics import CreateAPIView
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.serializers import ValidationError
from rest_framework.views import APIView

from accounts.serializers import RegisterUserSerializer, UserTokenObtainPairSerializer
from backend.utils import token_validation

class SignupView(CreateAPIView):
    """
    View for user signup.
    """

    permission_classes = [AllowAny]
    serializer_class = RegisterUserSerializer

    @swagger_auto_schema(
        operation_summary="Register a new user",
        request_body=RegisterUserSerializer,
        responses={
            201: openapi.Response(
                description="Registration successful with tokens",
                examples={
                    "application/json": {
                        "access": "eyJ0eXAiOiJKV1QiLCJhbGc...",
                        "refresh": "eyJ0eXAiOiJKV1QiLCJhbGc...",
                        "role": "Founder",
                        "company_id": None,
                        "message": "Registration successful. Thank you for joining us.",
                    }
                },
            )
        },
    )
    def post(self, request):
        """
        Handle user sign-up request.

        Args:
            request: HTTP request object.

        Returns:
            Response with tokens and success message.
        """

        # validate the incoming data
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)

        with transaction.atomic():
            user = serializer.save()
            user.save()

        # Generate tokens for the newly created user
        refresh = UserTokenObtainPairSerializer.get_token(user)
        
        # Get user role and company info
        from accounts.utils import get_user_company
        company = get_user_company(user)
        
        return Response(
            data={
                "access": str(refresh.access_token),
                "refresh": str(refresh),
                "role": user.role,
                "company_id": str(company.id) if company else None,
                "message": "Registration successful. Thank you for joining us.",
            },
            status=status.HTTP_201_CREATED,
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
