from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from sales.serializers.team_performance_combined import TeamPerformanceCombinedSerializer
from sales.views.api.team_performance import TeamPerformanceView
from sales.views.api.revenue_by_product import RevenueByProductView


class TeamPerformanceCombinedView(APIView):
    """
    Combined Team Performance API
    Returns both Team Performance Overview and Revenue by Product Line data
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        """Get combined Team Performance data"""
        # Get data from both views
        team_performance_view = TeamPerformanceView()
        revenue_by_product_view = RevenueByProductView()

        # Get team performance data
        team_performance_response = team_performance_view.get(request)
        if team_performance_response.status_code != status.HTTP_200_OK:
            return team_performance_response
        team_performance_data = team_performance_response.data

        # Get revenue by product data
        revenue_by_product_response = revenue_by_product_view.get(request)
        if revenue_by_product_response.status_code != status.HTTP_200_OK:
            return revenue_by_product_response
        revenue_by_product_data = revenue_by_product_response.data

        # Combine the data
        response_data = {
            "team_performance": team_performance_data,
            "revenue_by_product": revenue_by_product_data,
        }

        serializer = TeamPerformanceCombinedSerializer(data=response_data)
        if serializer.is_valid():
            return Response(serializer.validated_data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

