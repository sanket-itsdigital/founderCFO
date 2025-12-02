from drf_yasg.utils import swagger_auto_schema
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.serializers.user_info_serializer import UserInfoSerializer


class UserInfoAPIView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = UserInfoSerializer

    @swagger_auto_schema(
        operation_summary="Get current user basic info",
        responses={200: UserInfoSerializer},
    )
    def get(self, request, format=None):
        serializer = self.serializer_class(
            request.user,
            context={"request": request},
        )
        return Response(serializer.data)

    @swagger_auto_schema(
        operation_summary="Update current user basic info",
        request_body=UserInfoSerializer,
        responses={200: UserInfoSerializer},
    )
    def patch(self, request, format=None):
        serializer = self.serializer_class(
            request.user,
            data=request.data,
            partial=True,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)
