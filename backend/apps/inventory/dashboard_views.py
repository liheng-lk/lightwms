"""Dashboard statistics API endpoint."""
from datetime import timedelta

from django.db.models import Count, Sum, Q
from django.db.models.functions import TruncMonth
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema

from apps.inventory.models import Item, Category
from apps.operations.models import BorrowRecord, TakeRecord, ReplenishRecord


class DashboardStatsView(APIView):
    """Dashboard statistics for data visualization."""
    permission_classes = [IsAuthenticated]

    @extend_schema(
        responses={200: dict},
        tags=['Dashboard'],
        summary='Get dashboard statistics',
        description='Returns inventory trends, borrowing stats, top borrowed items, and category distribution.',
    )
    def get(self, request):
        now = timezone.now()
        six_months_ago = now - timedelta(days=180)

        # 1. Items added per month (last 6 months)
        inventory_trends = list(
            Item.objects.filter(
                created_at__gte=six_months_ago,
                is_active=True,
            )
            .annotate(month=TruncMonth('created_at'))
            .values('month')
            .annotate(count=Count('id'))
            .order_by('month')
        )

        # 2. Borrows per month (last 6 months)
        borrow_trends = list(
            BorrowRecord.objects.filter(
                created_at__gte=six_months_ago,
            )
            .annotate(month=TruncMonth('created_at'))
            .values('month')
            .annotate(count=Count('id'))
            .order_by('month')
        )

        # 3. Top 10 most borrowed items
        top_borrowed = list(
            BorrowRecord.objects.filter(
                created_at__gte=six_months_ago,
            )
            .values('item__name', 'item__sku')
            .annotate(borrow_count=Count('id'))
            .order_by('-borrow_count')[:10]
        )

        # 4. Category distribution (item count per category)
        category_distribution = list(
            Item.objects.filter(is_active=True)
            .values('category__name')
            .annotate(count=Count('id'))
            .order_by('-count')
        )
        # Handle items without category
        for entry in category_distribution:
            if entry['category__name'] is None:
                entry['category__name'] = '未分类'

        # 5. Take records per month (last 6 months)
        take_trends = list(
            TakeRecord.objects.filter(
                created_at__gte=six_months_ago,
            )
            .annotate(month=TruncMonth('created_at'))
            .values('month')
            .annotate(
                count=Count('id'),
                total_quantity=Sum('quantity'),
            )
            .order_by('month')
        )

        # 6. Replenish records per month (last 6 months)
        replenish_trends = list(
            ReplenishRecord.objects.filter(
                created_at__gte=six_months_ago,
            )
            .annotate(month=TruncMonth('created_at'))
            .values('month')
            .annotate(
                count=Count('id'),
                total_quantity=Sum('quantity'),
            )
            .order_by('month')
        )

        # Format dates for JSON serialization
        def format_trends(trends):
            return [
                {
                    'month': entry['month'].strftime('%Y-%m'),
                    'count': entry['count'],
                    **(
                        {'total_quantity': entry['total_quantity']}
                        if 'total_quantity' in entry else {}
                    ),
                }
                for entry in trends
            ]

        return Response({
            'inventory_trends': format_trends(inventory_trends),
            'borrow_trends': format_trends(borrow_trends),
            'top_borrowed': [
                {
                    'name': item['item__name'],
                    'sku': item['item__sku'],
                    'borrow_count': item['borrow_count'],
                }
                for item in top_borrowed
            ],
            'category_distribution': [
                {
                    'name': entry['category__name'],
                    'count': entry['count'],
                }
                for entry in category_distribution
            ],
            'take_trends': format_trends(take_trends),
            'replenish_trends': format_trends(replenish_trends),
        }, status=status.HTTP_200_OK)
