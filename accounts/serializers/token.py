from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from accounts.utils import get_user_company


class UserTokenObtainPairSerializer(TokenObtainPairSerializer):
    """Custom JWT serializer that injects role and company info into tokens."""

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token["role"] = user.role
        company = get_user_company(user)
        token["company_id"] = str(company.id) if company else None
        return token

    def validate(self, attrs):
        data = super().validate(attrs)
        data["role"] = self.user.role
        company = get_user_company(self.user)
        data["company_id"] = str(company.id) if company else None
        return data



