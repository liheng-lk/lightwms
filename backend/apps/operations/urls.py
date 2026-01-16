"""
URL configuration for operations app.
"""
from django.urls import path

from .views import (
    ItemBorrowView,
    ItemReturnView,
    BorrowRecordListView,
    BorrowRecordDeleteView,
    BorrowRecordBatchDeleteView,
    RecentBorrowersView,
    ItemTakeView,
    ItemReplenishView,
    TakeRecordListView,
    TakeRecordDeleteView,
    TakeRecordBatchDeleteView,
    ReplenishRecordListView,
    ReplenishRecordDeleteView,
    ReplenishRecordBatchDeleteView,
)

urlpatterns = [
    # Borrow records list and delete
    path('borrow-records/', BorrowRecordListView.as_view(), name='borrow-record-list'),
    path('borrow-records/<int:pk>/', BorrowRecordDeleteView.as_view(), name='borrow-record-delete'),
    path('borrow-records/batch-delete/', BorrowRecordBatchDeleteView.as_view(), name='borrow-record-batch-delete'),
    
    # Take records list and delete
    path('take-records/', TakeRecordListView.as_view(), name='take-record-list'),
    path('take-records/<int:pk>/', TakeRecordDeleteView.as_view(), name='take-record-delete'),
    path('take-records/batch-delete/', TakeRecordBatchDeleteView.as_view(), name='take-record-batch-delete'),
    
    # Replenish records list and delete
    path('replenish-records/', ReplenishRecordListView.as_view(), name='replenish-record-list'),
    path('replenish-records/<int:pk>/', ReplenishRecordDeleteView.as_view(), name='replenish-record-delete'),
    path('replenish-records/batch-delete/', ReplenishRecordBatchDeleteView.as_view(), name='replenish-record-batch-delete'),
    
    # Recent borrowers
    path('recent-borrowers/', RecentBorrowersView.as_view(), name='recent-borrowers'),
]

# Item-specific borrow/return/take/replenish endpoints are defined separately
# and included in the inventory URLs or main URLs
item_borrow_urlpatterns = [
    path('items/<int:pk>/borrow/', ItemBorrowView.as_view(), name='item-borrow'),
    path('items/<int:pk>/return/', ItemReturnView.as_view(), name='item-return'),
]

item_consumable_urlpatterns = [
    path('items/<int:pk>/take/', ItemTakeView.as_view(), name='item-take'),
    path('items/<int:pk>/replenish/', ItemReplenishView.as_view(), name='item-replenish'),
]
