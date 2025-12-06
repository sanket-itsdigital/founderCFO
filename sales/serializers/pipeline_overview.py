from rest_framework import serializers


class PipelineDealSerializer(serializers.Serializer):
    """Serializer for pipeline deal item"""
    deal_id = serializers.UUIDField()
    account_name = serializers.CharField()
    owner = serializers.CharField(allow_null=True, allow_blank=True, required=False)
    product = serializers.CharField(allow_null=True, allow_blank=True, required=False)
    amount = serializers.FloatField()
    amount_display = serializers.CharField()
    mrr = serializers.FloatField()
    mrr_display = serializers.CharField()
    stage = serializers.CharField()
    probability = serializers.FloatField()
    probability_display = serializers.CharField()
    close_date = serializers.DateField(allow_null=True, required=False)
    close_date_display = serializers.CharField(allow_null=True, allow_blank=True, required=False)
    status = serializers.CharField()


class PipelineOverviewSerializer(serializers.Serializer):
    """Serializer for Pipeline Overview response"""
    title = serializers.CharField()
    deals = PipelineDealSerializer(many=True)
    total_count = serializers.IntegerField()

