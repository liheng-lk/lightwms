'use client';

import { useState } from 'react';
import { useSearchParams, useRouter } from 'next/navigation';
import { Button } from '@/components/ui/button';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog';
import { ChevronLeft, ChevronRight, Plus, Upload, Download, FileSpreadsheet, MoreHorizontal, Printer, Trash2, X, MapPin, User } from 'lucide-react';
import { ItemFilters } from '@/components/items/item-filters';
import { ItemTable } from '@/components/items/item-table';
import { ItemForm } from '@/components/items/item-form';
import { ImportDialog } from '@/components/import-export/import-dialog';
import { BarcodePrintDialog } from '@/components/barcode/barcode-print-dialog';
import { BatchLocationDialog } from '@/components/items/batch-location-dialog';
import { BatchOwnerDialog } from '@/components/items/batch-owner-dialog';
import { PageHelp } from '@/components/ui/help-tooltip';
import { useItems, useDeleteItems } from '@/lib/hooks/use-items';
import { usePermissions } from '@/lib/hooks/use-permissions';
import { useAuth } from '@/providers/auth-provider';
import { useExportItems, useDownloadTemplate } from '@/lib/hooks/use-import-export';
import type { Item } from '@/lib/types';

const PAGE_SIZES = [10, 20, 50];

export default function ItemsPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { canCreate, canDelete } = usePermissions();
  const { user } = useAuth();
  const [showCreateDialog, setShowCreateDialog] = useState(false);
  const [showImportDialog, setShowImportDialog] = useState(false);
  const [editingItem, setEditingItem] = useState<Item | undefined>(undefined);
  // Batch selection state for barcode printing
  const [selectedItemIds, setSelectedItemIds] = useState<number[]>([]);
  const [showPrintDialog, setShowPrintDialog] = useState(false);
  const [showDeleteDialog, setShowDeleteDialog] = useState(false);
  const [showBatchLocationDialog, setShowBatchLocationDialog] = useState(false);
  const [showBatchOwnerDialog, setShowBatchOwnerDialog] = useState(false);
  
  // Permission checks
  const isSuperAdmin = user?.role === 'super_admin';
  const isItemManager = user?.role === 'item_manager';
  const canManageBulkActions = isSuperAdmin || isItemManager;
  const canBatchUpdateLocation = canManageBulkActions;
  const canBatchUpdateOwner = isSuperAdmin;
  
  const keyword = searchParams.get('keyword') || undefined;
  const category = searchParams.get('category') ? Number(searchParams.get('category')) : undefined;
  const location = searchParams.get('location') ? Number(searchParams.get('location')) : undefined;
  const status = searchParams.get('status') || undefined;
  const item_type = searchParams.get('type') || undefined;
  const page = Number(searchParams.get('page')) || 1;
  const page_size = Number(searchParams.get('page_size')) || 20;
  
  const { data, isLoading, refetch } = useItems({
    keyword,
    category,
    location,
    status,
    item_type,
    page,
    page_size,
  });

  const exportMutation = useExportItems();
  const downloadTemplateMutation = useDownloadTemplate();
  const deleteItemsMutation = useDeleteItems();
  
  const totalPages = data ? Math.ceil(data.count / page_size) : 0;
  
  const updateParams = (updates: Record<string, string | number | undefined>) => {
    const params = new URLSearchParams(searchParams.toString());
    Object.entries(updates).forEach(([key, value]) => {
      if (value !== undefined && value !== '') {
        params.set(key, String(value));
      } else {
        params.delete(key);
      }
    });
    router.push(`/items?${params.toString()}`);
  };
  
  const goToPage = (newPage: number) => {
    updateParams({ page: newPage });
  };
  
  const changePageSize = (newSize: string) => {
    updateParams({ page_size: Number(newSize), page: 1 });
  };

  const handleCreateSuccess = () => {
    refetch();
  };

  const handleEditItem = (item: Item) => {
    setEditingItem(item);
  };

  const handleEditDialogClose = (open: boolean) => {
    if (!open) {
      setEditingItem(undefined);
    }
  };

  const handleEditSuccess = () => {
    setEditingItem(undefined);
    refetch();
  };

  const handleImportSuccess = () => {
    refetch();
  };

  const handleExport = () => {
    // Export with current filters
    exportMutation.mutate({
      category,
      location,
      status,
      item_type,
    });
  };

  const handleDownloadTemplate = () => {
    downloadTemplateMutation.mutate();
  };

  // Get selected items for printing (only items with barcodes)
  const selectedItems = (data?.results || []).filter(item => selectedItemIds.includes(item.id));
  const selectedItemsWithBarcode = selectedItems.filter(item => item.barcode);

  const handlePrintDialogClose = () => {
    setShowPrintDialog(false);
    // Clear selection after closing print dialog
    setSelectedItemIds([]);
  };

  const handleBatchDelete = () => {
    deleteItemsMutation.mutate(selectedItemIds, {
      onSuccess: () => {
        setSelectedItemIds([]);
        setShowDeleteDialog(false);
        refetch();
      },
    });
  };

  const handleClearSelection = () => {
    setSelectedItemIds([]);
  };

  const handleBatchLocationSuccess = () => {
    setSelectedItemIds([]);
    refetch();
  };

  const handleBatchOwnerSuccess = () => {
    setSelectedItemIds([]);
    refetch();
  };
  
  return (
    <div className="space-y-4">
      {/* 页面标题 */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <h1 className="text-2xl font-semibold">物品管理</h1>
          <PageHelp
            title="物品管理使用指南"
            tips={[
              '点击「新增物品」添加新的库存物品',
              '使用筛选器按分类、库位、状态快速查找',
              '没有的物品直接删除',
              '管理员支持批量导入导出物品数据',
              '勾选物品后可批量打印条码标签',
            ]}
          />
        </div>
        <div className="flex items-center gap-2">
          {/* Batch actions - show when items are selected */}
          {selectedItemIds.length > 0 && (
            <>
              {selectedItemsWithBarcode.length > 0 && (
                <Button 
                  variant="outline"
                  onClick={() => setShowPrintDialog(true)}
                >
                  <Printer className="h-4 w-4 mr-2" />
                  打印条码 ({selectedItemsWithBarcode.length})
                </Button>
              )}
              {canDelete() && (
                <Button 
                  variant="outline"
                  className="text-destructive"
                  onClick={() => setShowDeleteDialog(true)}
                >
                  <Trash2 className="h-4 w-4 mr-2" />
                  删除 ({selectedItemIds.length})
                </Button>
              )}
            </>
          )}
          {/* Import/Export dropdown is a management-only surface. */}
          {canManageBulkActions && (
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="outline">
                  <MoreHorizontal className="h-4 w-4 mr-2" />
                  更多操作
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end">
                {isSuperAdmin && (
                  <DropdownMenuItem onClick={() => setShowImportDialog(true)}>
                    <Upload className="h-4 w-4 mr-2" />
                    导入物品
                  </DropdownMenuItem>
                )}
                <DropdownMenuItem 
                  onClick={handleExport}
                  disabled={exportMutation.isPending}
                >
                  <Download className="h-4 w-4 mr-2" />
                  {exportMutation.isPending ? '导出中...' : '导出物品'}
                </DropdownMenuItem>
                <DropdownMenuItem 
                  onClick={handleDownloadTemplate}
                  disabled={downloadTemplateMutation.isPending}
                >
                  <FileSpreadsheet className="h-4 w-4 mr-2" />
                  下载导入模板
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          )}
          
          {canCreate() && (
            <Button onClick={() => setShowCreateDialog(true)}>
              <Plus className="h-4 w-4 mr-2" />
              新增物品
            </Button>
          )}
        </div>
      </div>
      
      {/* 筛选器 */}
      <ItemFilters />

      {/* 批量操作栏 */}
      {selectedItemIds.length > 0 && (
        <div className="flex items-center gap-4 p-3 bg-muted rounded-lg">
          <span className="text-sm">
            已选择 <strong>{selectedItemIds.length}</strong> 个物品
          </span>
          {canBatchUpdateLocation && (
            <Button variant="outline" size="sm" onClick={() => setShowBatchLocationDialog(true)}>
              <MapPin className="h-4 w-4 mr-1" />
              批量迁移库位
            </Button>
          )}
          {canBatchUpdateOwner && (
            <Button variant="outline" size="sm" onClick={() => setShowBatchOwnerDialog(true)}>
              <User className="h-4 w-4 mr-1" />
              批量更改负责人
            </Button>
          )}
          <Button variant="ghost" size="sm" onClick={handleClearSelection}>
            <X className="h-4 w-4 mr-1" />
            取消选择
          </Button>
        </div>
      )}
      
      {/* 搜索关键词提示 */}
      {keyword && (
        <div className="text-sm text-muted-foreground">
          搜索 &quot;{keyword}&quot; 的结果，共 {data?.count || 0} 条
        </div>
      )}
      
      {/* 物品表格 */}
      <ItemTable 
        items={data?.results || []} 
        isLoading={isLoading} 
        onEdit={handleEditItem}
        selectable={true}
        selectedIds={selectedItemIds}
        onSelectionChange={setSelectedItemIds}
      />
      
      {/* 分页 */}
      {data && data.count > 0 && (
        <div className="flex items-center justify-between">
          <div className="text-sm text-muted-foreground">
            共 {data.count} 条，第 {page} / {totalPages} 页
          </div>
          
          <div className="flex items-center gap-4">
            {/* 每页条数 */}
            <div className="flex items-center gap-2">
              <span className="text-sm text-muted-foreground">每页</span>
              <Select value={String(page_size)} onValueChange={changePageSize}>
                <SelectTrigger className="w-[70px]">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {PAGE_SIZES.map((size) => (
                    <SelectItem key={size} value={String(size)}>
                      {size}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <span className="text-sm text-muted-foreground">条</span>
            </div>
            
            {/* 翻页按钮 */}
            <div className="flex items-center gap-1">
              <Button
                variant="outline"
                size="icon"
                onClick={() => goToPage(page - 1)}
                disabled={page <= 1}
              >
                <ChevronLeft className="h-4 w-4" />
              </Button>
              <Button
                variant="outline"
                size="icon"
                onClick={() => goToPage(page + 1)}
                disabled={page >= totalPages}
              >
                <ChevronRight className="h-4 w-4" />
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* 新增物品弹窗 */}
      <ItemForm
        open={showCreateDialog}
        onOpenChange={setShowCreateDialog}
        onSuccess={handleCreateSuccess}
      />

      {/* 编辑物品弹窗 */}
      <ItemForm
        item={editingItem}
        open={!!editingItem}
        onOpenChange={handleEditDialogClose}
        onSuccess={handleEditSuccess}
      />

      {/* 导入物品弹窗 */}
      {isSuperAdmin && (
        <ImportDialog
          open={showImportDialog}
          onOpenChange={setShowImportDialog}
          onSuccess={handleImportSuccess}
        />
      )}

      {/* 批量打印条码弹窗 */}
      <BarcodePrintDialog
        items={selectedItemsWithBarcode}
        open={showPrintDialog}
        onOpenChange={(open) => {
          if (!open) handlePrintDialogClose();
          else setShowPrintDialog(open);
        }}
      />

      {/* 批量删除确认弹窗 */}
      <AlertDialog open={showDeleteDialog} onOpenChange={setShowDeleteDialog}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>确认批量删除</AlertDialogTitle>
            <AlertDialogDescription>
              确定要删除选中的 {selectedItemIds.length} 个物品吗？此操作无法撤销。
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>取消</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleBatchDelete}
              disabled={deleteItemsMutation.isPending}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              {deleteItemsMutation.isPending ? '删除中...' : '确认删除'}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      {/* 批量迁移库位弹窗 */}
      <BatchLocationDialog
        open={showBatchLocationDialog}
        onOpenChange={setShowBatchLocationDialog}
        selectedItemIds={selectedItemIds}
        onSuccess={handleBatchLocationSuccess}
      />

      {/* 批量更改负责人弹窗 */}
      <BatchOwnerDialog
        open={showBatchOwnerDialog}
        onOpenChange={setShowBatchOwnerDialog}
        selectedItemIds={selectedItemIds}
        onSuccess={handleBatchOwnerSuccess}
      />
    </div>
  );
}
