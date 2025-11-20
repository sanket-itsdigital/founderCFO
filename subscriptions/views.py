from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import generics, permissions, status
from rest_framework.response import Response

from accounts.permissions import IsFounder
from accounts.utils import get_user_company
from subscriptions.models import CompanySubscription, SubscriptionPlan
from subscriptions.serializers import (
    CompanySubscriptionSerializer,
    SubscriptionPlanSerializer,
    SubscriptionPurchaseSerializer,
)


class SubscriptionPlanListView(generics.ListAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = SubscriptionPlanSerializer
    queryset = SubscriptionPlan.objects.filter(is_active=True).order_by("price")


class CompanySubscriptionStatusView(generics.GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = CompanySubscriptionSerializer

    @swagger_auto_schema(
        operation_summary="Get current company's subscription status",
        responses={
            200: CompanySubscriptionSerializer,
            400: openapi.Response(
                description="No company associated",
                examples={
                    "application/json": {
                        "detail": "No company associated with this user."
                    }
                },
            ),
        },
    )
    def get(self, request, *args, **kwargs):
        company = get_user_company(request.user)
        if not company:
            return Response(
                {"detail": "No company associated with this user."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        subscription = (
            CompanySubscription.objects.filter(company=company)
            .order_by("-end_date")
            .first()
        )

        if not subscription:
            return Response(
                {
                    "active": False,
                    "message": "No subscription found",
                },
                status=status.HTTP_200_OK,
            )

        serializer = self.get_serializer(subscription)
        return Response(serializer.data, status=status.HTTP_200_OK)


class SubscriptionPurchaseView(generics.GenericAPIView):
    permission_classes = [permissions.IsAuthenticated, IsFounder]
    serializer_class = SubscriptionPurchaseSerializer

    @swagger_auto_schema(
        operation_summary="Purchase a subscription plan",
        request_body=SubscriptionPurchaseSerializer,
        responses={201: CompanySubscriptionSerializer},
    )
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        subscription = serializer.save()
        response_serializer = CompanySubscriptionSerializer(subscription)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)
