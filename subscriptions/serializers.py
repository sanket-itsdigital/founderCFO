from datetime import timedelta

from django.utils import timezone
from rest_framework import serializers

from accounts.utils import get_user_company
from subscriptions.models import CompanySubscription, SubscriptionPlan


class SubscriptionPlanSerializer(serializers.ModelSerializer):
    class Meta:
        model = SubscriptionPlan
        fields = (
            "id",
            "name",
            "price",
            "duration_days",
            "description",
        )


class CompanySubscriptionSerializer(serializers.ModelSerializer):
    plan = SubscriptionPlanSerializer(read_only=True)
    days_remaining = serializers.IntegerField(read_only=True)
    active = serializers.SerializerMethodField()

    class Meta:
        model = CompanySubscription
        fields = (
            "id",
            "plan",
            "start_date",
            "end_date",
            "status",
            "amount_paid",
            "days_remaining",
            "active",
        )

    def get_active(self, obj):
        return obj.is_active


class SubscriptionPurchaseSerializer(serializers.Serializer):
    plan_id = serializers.UUIDField()
    notes = serializers.CharField(required=False, allow_blank=True)

    def validate(self, attrs):
        request = self.context.get("request")
        plan_id = attrs.get("plan_id")
        try:
            plan = SubscriptionPlan.objects.get(id=plan_id, is_active=True)
        except SubscriptionPlan.DoesNotExist:
            raise serializers.ValidationError({"plan_id": "Selected plan is invalid."})

        company = get_user_company(request.user)
        if not company:
            raise serializers.ValidationError("You must be associated with a company.")

        attrs["plan"] = plan
        attrs["company"] = company
        attrs["user"] = request.user
        return attrs

    def save(self, **kwargs):
        plan = self.validated_data["plan"]
        company = self.validated_data["company"]
        user = self.validated_data["user"]
        notes = self.validated_data.get("notes", "")

        latest_active = (
            CompanySubscription.objects.filter(
                company=company,
                status=CompanySubscription.Status.ACTIVE,
                end_date__gte=timezone.now().date(),
            )
            .order_by("-end_date")
            .first()
        )

        start_date = timezone.now().date()
        if latest_active:
            start_date = latest_active.end_date + timedelta(days=1)

        subscription = CompanySubscription.objects.create(
            company=company,
            plan=plan,
            purchased_by=user,
            amount_paid=plan.price,
            start_date=start_date,
            end_date=start_date + timedelta(days=plan.duration_days),
            notes=notes,
        )

        return subscription
