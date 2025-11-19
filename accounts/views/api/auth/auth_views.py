from rest_framework import status
from rest_framework.generics import CreateAPIView
from rest_framework.response import Response
from rest_framework_simplejwt.views import TokenObtainPairView


from accounts.serializers import LogoutSerializer
from accounts.serializers import UserProfileSerializer
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from backend.enums import VerificationStatusChoices, UserRoleChoices


class SigninView(TokenObtainPairView):
    def post(self, request, *args, **kwargs):
        # Use the TokenObtainPairSerializer to validate the request data
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        if (
            status == VerificationStatusChoices.PENDING
            and role == UserRoleChoices.FOUNDER
        ):
            message = "Your account is pending verification. Please wait for approval before logging in. Thank you for your patience."
            return Response(
                data={"message": message}, status=status.HTTP_401_UNAUTHORIZED
            )
        elif status == VerificationStatusChoices.REJECTED:
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
        }

        # Return the response with the access and refresh tokens, along with the user's role
        return Response(response_data)


class LogoutAPIView(CreateAPIView):
    """
    API view for logging out a user by invalidating the refresh token.
    """

    serializer_class = LogoutSerializer

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

    def get(self, request):
        serializer = UserProfileSerializer(request.user, context={"request": request})
        return Response(serializer.data, status=status.HTTP_200_OK)

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

    def put(self, request):
        return self.patch(request)
