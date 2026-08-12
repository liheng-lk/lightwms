"""
URL configuration for inventory app.
"""
from django.urls import path

from .views import (
    ItemByBarcodeView,
    SearchView,
)
from .reference_views import (
    WarehouseListCreateView,
    WarehouseDetailView,
    WarehouseDeactivateView,
    WarehouseDeleteView,
    WarehouseBatchDeleteView,
    LocationListCreateView,
    LocationTreeView,
    LocationDetailView,
    LocationDeactivateView,
    CategoryListCreateView,
    CategoryTreeView,
    CategoryDetailView,
    CategoryDeactivateView,
    CategoryDeleteView,
    CategoryBatchDeleteView,
)
from .permission_views import (
    ItemDetailView,
    ItemDeactivateView,
    ItemDeleteView,
    ItemBatchDeleteView,
    ItemGenerateBarcodeView,
    ItemImageListCreateView,
    ItemImageDetailView,
    ItemImageSetPrimaryView,
    ItemBatchUpdateLocationView,
    ItemBatchUpdateOwnerView,
)
from .validated_views import ItemListCreateView, ItemCreateWithInvoiceView

from apps.imports.permission_views import (
    ItemImportView,
    ItemExportView,
    ItemImportTemplateView,
    BorrowRecordExportView,
    TakeRecordExportView,
    ReplenishRecordExportView,
)

app_name = 'inventory'

urlpatterns = [
    # Export endpoints (must be before dynamic routes)
    path('export/borrow-records/', BorrowRecordExportView.as_view(), name='borrow-record-export'),
    path('export/take-records/', TakeRecordExportView.as_view(), name='take-record-export'),
    path('export/replenish-records/', ReplenishRecordExportView.as_view(), name='replenish-record-export'),

    # Warehouse endpoints
    path('warehouses/', WarehouseListCreateView.as_view(), name='warehouse-list-create'),
    path('warehouses/batch-delete/', WarehouseBatchDeleteView.as_view(), name='warehouse-batch-delete'),
    path('warehouses/<int:pk>/', WarehouseDetailView.as_view(), name='warehouse-detail'),
    path('warehouses/<int:pk>/deactivate/', WarehouseDeactivateView.as_view(), name='warehouse-deactivate'),
    path('warehouses/<int:pk>/delete/', WarehouseDeleteView.as_view(), name='warehouse-delete'),

    # Location endpoints
    path('locations/', LocationListCreateView.as_view(), name='location-list-create'),
    path('locations/tree/', LocationTreeView.as_view(), name='location-tree'),
    path('locations/<int:pk>/', LocationDetailView.as_view(), name='location-detail'),
    path('locations/<int:pk>/deactivate/', LocationDeactivateView.as_view(), name='location-deactivate'),

    # Category endpoints
    path('categories/', CategoryListCreateView.as_view(), name='category-list-create'),
    path('categories/tree/', CategoryTreeView.as_view(), name='category-tree'),
    path('categories/batch-delete/', CategoryBatchDeleteView.as_view(), name='category-batch-delete'),
    path('categories/<int:pk>/', CategoryDetailView.as_view(), name='category-detail'),
    path('categories/<int:pk>/deactivate/', CategoryDeactivateView.as_view(), name='category-deactivate'),
    path('categories/<int:pk>/delete/', CategoryDeleteView.as_view(), name='category-delete'),

    # Item endpoints (static routes MUST come before dynamic <int:pk> routes)
    path('items/export/', ItemExportView.as_view(), name='item-export'),
    path('items/import/', ItemImportView.as_view(), name='item-import'),
    path('items/import-template/', ItemImportTemplateView.as_view(), name='item-import-template'),
    path('items/with-invoice/', ItemCreateWithInvoiceView.as_view(), name='item-create-with-invoice'),
    path('items/batch-delete/', ItemBatchDeleteView.as_view(), name='item-batch-delete'),
    path('items/batch-update-location/', ItemBatchUpdateLocationView.as_view(), name='item-batch-update-location'),
    path('items/batch-update-owner/', ItemBatchUpdateOwnerView.as_view(), name='item-batch-update-owner'),
    path('items/by-barcode/<str:barcode>/', ItemByBarcodeView.as_view(), name='item-by-barcode'),
    path('items/', ItemListCreateView.as_view(), name='item-list-create'),
    path('items/<int:pk>/', ItemDetailView.as_view(), name='item-detail'),
    path('items/<int:pk>/deactivate/', ItemDeactivateView.as_view(), name='item-deactivate'),
    path('items/<int:pk>/delete/', ItemDeleteView.as_view(), name='item-delete'),
    path('items/<int:pk>/generate-barcode/', ItemGenerateBarcodeView.as_view(), name='item-generate-barcode'),

    # Item image endpoints
    path('items/<int:pk>/images/', ItemImageListCreateView.as_view(), name='item-image-list-create'),
    path('items/<int:pk>/images/<int:image_id>/', ItemImageDetailView.as_view(), name='item-image-detail'),
    path('items/<int:pk>/images/<int:image_id>/set-primary/', ItemImageSetPrimaryView.as_view(), name='item-image-set-primary'),

    # Search endpoint
    path('search/', SearchView.as_view(), name='search'),
]
