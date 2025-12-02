from rest_framework import serializers
from financial.models.audit_trail import AuditTrail


class AuditTrailSerializer(serializers.ModelSerializer):
    """Serializer for AuditTrail"""
    action_display = serializers.CharField(source='get_action_display', read_only=True)
    entity_type_display = serializers.CharField(source='get_entity_type_display', read_only=True)
    user_email = serializers.CharField(source='user.email', read_only=True, allow_null=True)
    user_name = serializers.SerializerMethodField()
    timestamp_display = serializers.SerializerMethodField()
    changes_display = serializers.SerializerMethodField()

    class Meta:
        model = AuditTrail
        fields = [
            "id",
            "action",
            "action_display",
            "entity_type",
            "entity_type_display",
            "entity_id",
            "reference",
            "details",
            "changes",
            "changes_display",
            "user",
            "user_email",
            "user_name",
            "created_at",
            "timestamp_display",
        ]

    def get_user_name(self, obj):
        if obj.user:
            return obj.user.full_name or obj.user.email
        return "System"

    def get_timestamp_display(self, obj):
        return obj.created_at.strftime("%d %b %Y %H:%M")

    def get_changes_display(self, obj):
        if obj.changes:
            # Format changes as "old -> new"
            if isinstance(obj.changes, dict) and "old" in obj.changes and "new" in obj.changes:
                import json
                old_str = json.dumps(obj.changes["old"])
                new_str = json.dumps(obj.changes["new"])
                return f"{old_str} -> {new_str}"
        return None

