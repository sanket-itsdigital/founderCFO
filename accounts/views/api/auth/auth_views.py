from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.generics import CreateAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework.views import APIView
from rest_framework.generics import UpdateAPIView
from accounts.serializers import (
    LogoutSerializer,
    UserProfileSerializer,
    UserTokenObtainPairSerializer,
)
from accounts.serializers.auth import ChangePasswordSerializer
from backend.enums import UserRoleChoices, VerificationStatusChoices


token_response_schema = openapi.Schema(
    type=openapi.TYPE_OBJECT,
    properties={
        "access": openapi.Schema(
            type=openapi.TYPE_STRING, description="JWT access token"
        ),
        "refresh": openapi.Schema(
            type=openapi.TYPE_STRING, description="JWT refresh token"
        ),
        "role": openapi.Schema(
            type=openapi.TYPE_STRING,
            description="Role embedded in the token",
        ),
        "company_id": openapi.Schema(
            type=openapi.TYPE_STRING,
            nullable=True,
            description="Associated company ID embedded in the token",
        ),
    },
)


class SigninView(TokenObtainPairView):
    serializer_class = UserTokenObtainPairSerializer

    @swagger_auto_schema(
        operation_summary="Obtain JWT tokens",
        request_body=UserTokenObtainPairSerializer,
        responses={
            200: openapi.Response(description="Tokens", schema=token_response_schema)
        },
    )
    def post(self, request, *args, **kwargs):
        # Use the TokenObtainPairSerializer to validate the request data
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = getattr(serializer, "user", None)
        if user:
            user_status = getattr(user, "status", None)
            user_role = getattr(user, "role", None)
            if (
                user_status == VerificationStatusChoices.PENDING
                and user_role == UserRoleChoices.FOUNDER
            ):
                message = "Your account is pending verification. Please wait for approval before logging in. Thank you for your patience."
                return Response(
                    data={"message": message}, status=status.HTTP_401_UNAUTHORIZED
                )
            if user_status == VerificationStatusChoices.REJECTED:
                message = "Your account verification was rejected. Please contact support for further assistance."
                return Response(
                    data={"message": message}, status=status.HTTP_401_UNAUTHORIZED
                )

        # Get the token data from the superclass method
        token_data = serializer.validated_data

        # Add the user's name to the response data
        response_data = {
            "access": token_data["access"],
            "refresh": token_data["refresh"],
            "role": token_data.get("role"),
            "company_id": token_data.get("company_id"),
        }

        # Return the response with the access and refresh tokens, along with the user's role
        return Response(response_data)


class LogoutAPIView(CreateAPIView):
    """
    API view for logging out a user by invalidating the refresh token.
    """

    serializer_class = LogoutSerializer

    @swagger_auto_schema(
        operation_summary="Logout user",
        request_body=LogoutSerializer,
        responses={
            200: openapi.Response(
                description="Logout success",
                examples={
                    "application/json": {"message": "User successfully logged out."}
                },
            )
        },
    )
    def create(self, request, *args, **kwargs):
        """
        Handle POST requests to invalidate the refresh token and log the user out.

        Returns:
            Response: JSON response indicating the success or failure of the logout operation.
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Return success response
        return Response(
            {"message": "User successfully logged out."}, status=status.HTTP_200_OK
        )


class ProfileAPIView(APIView):
    """Return the authenticated user's profile (GET).

    Optionally allow the user to update their profile via PUT/PATCH in future.
    """

    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="Get current user profile",
        responses={200: UserProfileSerializer},
    )
    def get(self, request):
        serializer = UserProfileSerializer(request.user, context={"request": request})
        return Response(serializer.data, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        operation_summary="Update current user profile",
        request_body=UserProfileSerializer,
        responses={200: UserProfileSerializer},
    )
    def patch(self, request):
        serializer = UserProfileSerializer(
            request.user,
            data=request.data,
            partial=True,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        operation_summary="Replace current user profile",
        request_body=UserProfileSerializer,
        responses={200: UserProfileSerializer},
    )
    def put(self, request):
        return self.patch(request)


class ChangePasswordAPIView(UpdateAPIView):
    """
    API view for changing the user's password.
    """

    http_method_names = ["patch"]
    # Serializer class for handling password change
    serializer_class = ChangePasswordSerializer

    # Permission class to ensure user is authenticated
    permission_classes = (IsAuthenticated,)

    def update(self, request, *args, **kwargs):
        """
        Handle password change request.

        Args:
            request: HTTP request object.
            *args: Additional positional arguments.
            **kwargs: Additional keyword arguments.

        Returns:
            Response indicating success or failure of password change.
        """

        serializer = self.get_serializer(data=request.data)  # Get serializer instance
        serializer.is_valid(raise_exception=True)  # Validate the serializer data
        serializer.save()  # Save the updated password
        return generic_response(
            status_code=status.HTTP_200_OK,
            message="Password changed successfully.",
        )
