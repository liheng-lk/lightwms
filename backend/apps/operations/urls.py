"""
URL configuration for operations app.
"""
from django.urls import path

from .views import (
    BorrowRecordDeleteView,
    BorrowRecordBatchDeleteView,
)
from .ledger_views import (
    TakeRecordDeleteView,
    TakeRecordBatchDeleteView,
    ReplenishRecordDeleteView,
    ReplenishRecordBatchDeleteView,
)
from .permission_views import (
    ItemBorrowView,
    ItemReturnView,
    BorrowRecordListView,
    RecentBorrowersView,
    ItemTakeView,
    ItemReplenishView,
    TakeRecordListView,
    ReplenishRecordListView,
)

urlpatterns = [
    path('borrow-records/', BorrowRecordListView.as_view(), name='borrow-record-list'),
    path('borrow-records/<int:pk>/', BorrowRecordDeleteView.as_view(), name='borrow-record-delete'),
    path('borrow-records/batch-delete/', BorrowRecordBatchDeleteView.as_view(), name='borrow-record-batch-delete'),

    path('take-records/', TakeRecordListView.as_view(), name='take-record-list'),
    path('take-records/<int:pk>/', TakeRecordDeleteView.as_view(), name='take-record-delete'),
    path('take-records/batch-delete/', TakeRecordBatchDeleteView.as_view(), name='take-record-batch-delete'),

    path('replenish-records/', ReplenishRecordListView.as_view(), name='replenish-record-list'),
    path('replenish-records/<int:pk>/', ReplenishRecordDeleteView.as_view(), name='replenish-record-delete'),
    path('replenish-records/batch-delete/', ReplenishRecordBatchDeleteView.as_view(), name='replenish-record-batch-delete'),

    path('recent-borrowers/', RecentBorrowersView.as_view(), name='recent-borrowers'),
]

item_borrow_urlpatterns = [
    path('items/<int:pk>/borrow/', ItemBorrowView.as_view(), name='item-borrow'),
    path('items/<int:pk>/return/', ItemReturnView.as_view(), name='item-return'),
]

item_consumable_urlpatterns = [
    path('items/<int:pk>/take/', ItemTakeView.as_view(), name='item-take'),
    path('items/<int:pk>/replenish/', ItemReplenishView.as_view(), name='item-replenish'),
]
