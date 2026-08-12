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
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog';
import { ChevronLeft, ChevronRight, Plus, Trash2, X } from 'lucide-react';
import { WarehouseTable } from '@/components/warehouses/warehouse-table';
import { WarehouseForm } from '@/components/warehouses/warehouse-form';
import { PageHelp } from '@/components/ui/help-tooltip';
import { useWarehouses, useDeleteWarehouses } from '@/lib/hooks/use-warehouses';
import { useAuth } from '@/providers/auth-provider';
import type { Warehouse } from '@/lib/types';

const PAGE_SIZES = [10, 20, 50];

export default function WarehousesPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { user } = useAuth();
  const canManage = user?.role === 'super_admin' || user?.role === 'item_manager';
  const isSuperAdmin = user?.role === 'super_admin';
  const [showCreateDialog, setShowCreateDialog] = useState(false);
  const [editingWarehouse, setEditingWarehouse] = useState<Warehouse | undefined>(undefined);
  const [selectedIds, setSelectedIds] = useState<number[]>([]);
  const [showDeleteDialog, setShowDeleteDialog] = useState(false);
  
  const page = Number(searchParams.get('page')) || 1;
  const page_size = Number(searchParams.get('page_size')) || 20;
  
  const { data, isLoading, refetch } = useWarehouses({ page, page_size });
  const deleteWarehousesMutation = useDeleteWarehouses();
  const totalPages = data ? Math.ceil(data.count / page_size) : 0;
  
  const updateParams = (updates: Record<string, string | number | undefined>) => {
    const params = new URLSearchParams(searchParams.toString());
    Object.entries(updates).forEach(([key, value]) => {
      if (value !== undefined && value !== '') params.set(key, String(value));
      else params.delete(key);
    });
    router.push(`/warehouses?${params.toString()}`);
  };
  
  const goToPage = (newPage: number) => updateParams({ page: newPage });
  const changePageSize = (newSize: string) => updateParams({ page_size: Number(newSize), page: 1 });
  const handleCreateSuccess = () => refetch();
  const handleEditWarehouse = (warehouse: Warehouse) => {
    if (canManage) setEditingWarehouse(warehouse);
  };
  const handleEditDialogClose = (open: boolean) => {
    if (!open) setEditingWarehouse(undefined);
  };
  const handleEditSuccess = () => {
    setEditingWarehouse(undefined);
    refetch();
  };
  const handleDeactivateSuccess = () => refetch();
  const handleBatchDelete = () => {
    if (!isSuperAdmin) return;
    deleteWarehousesMutation.mutate(selectedIds, {
      onSuccess: () => {
        setSelectedIds([]);
        setShowDeleteDialog(false);
        refetch();
      },
    });
  };
  const handleClearSelection = () => setSelectedIds([]);
  
  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <h1 className="text-2xl font-semibold">仓库管理</h1>
          <PageHelp
            title="仓库管理使用指南"
            tips={[
              '仓库是物品存放的顶层容器',
              '每个仓库可以包含多个库位',
              '物品管理员和超级管理员可创建、编辑和停用有效仓库',
              '停用仓库后，其下库位会从普通查询中隐藏并停止用于新库存',
              '批量永久删除属于全局破坏性操作，仅超级管理员可执行',
            ]}
          />
        </div>
        <div className="flex items-center gap-2">
          {isSuperAdmin && selectedIds.length > 0 && (
            <Button 
              variant="outline"
              className="text-destructive"
              onClick={() => setShowDeleteDialog(true)}
            >
              <Trash2 className="h-4 w-4 mr-2" />
              删除 ({selectedIds.length})
            </Button>
          )}
          {canManage && (
            <Button onClick={() => setShowCreateDialog(true)}>
              <Plus className="h-4 w-4 mr-2" />
              新增仓库
            </Button>
          )}
        </div>
      </div>

      {isSuperAdmin && selectedIds.length > 0 && (
        <div className="flex items-center gap-4 p-3 bg-muted rounded-lg">
          <span className="text-sm">
            已选择 <strong>{selectedIds.length}</strong> 个仓库
          </span>
          <Button variant="ghost" size="sm" onClick={handleClearSelection}>
            <X className="h-4 w-4 mr-1" />
            取消选择
          </Button>
        </div>
      )}
      
      <WarehouseTable 
        warehouses={data?.results || []} 
        isLoading={isLoading} 
        onEdit={canManage ? handleEditWarehouse : undefined}
        onDeactivateSuccess={canManage ? handleDeactivateSuccess : undefined}
        selectable={isSuperAdmin}
        selectedIds={selectedIds}
        onSelectionChange={isSuperAdmin ? setSelectedIds : undefined}
        canManage={canManage}
      />
      
      {data && data.count > 0 && (
        <div className="flex items-center justify-between">
          <div className="text-sm text-muted-foreground">
            共 {data.count} 条，第 {page} / {totalPages} 页
          </div>
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2">
              <span className="text-sm text-muted-foreground">每页</span>
              <Select value={String(page_size)} onValueChange={changePageSize}>
                <SelectTrigger className="w-[70px]"><SelectValue /></SelectTrigger>
                <SelectContent>
                  {PAGE_SIZES.map((size) => (
                    <SelectItem key={size} value={String(size)}>{size}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <span className="text-sm text-muted-foreground">条</span>
            </div>
            <div className="flex items-center gap-1">
              <Button variant="outline" size="icon" onClick={() => goToPage(page - 1)} disabled={page <= 1}>
                <ChevronLeft className="h-4 w-4" />
              </Button>
              <Button variant="outline" size="icon" onClick={() => goToPage(page + 1)} disabled={page >= totalPages}>
                <ChevronRight className="h-4 w-4" />
              </Button>
            </div>
          </div>
        </div>
      )}

      {canManage && (
        <>
          <WarehouseForm
            open={showCreateDialog}
            onOpenChange={setShowCreateDialog}
            onSuccess={handleCreateSuccess}
          />
          <WarehouseForm
            warehouse={editingWarehouse}
            open={!!editingWarehouse}
            onOpenChange={handleEditDialogClose}
            onSuccess={handleEditSuccess}
          />
        </>
      )}

      {isSuperAdmin && (
        <AlertDialog open={showDeleteDialog} onOpenChange={setShowDeleteDialog}>
          <AlertDialogContent>
            <AlertDialogHeader>
              <AlertDialogTitle>确认批量删除</AlertDialogTitle>
              <AlertDialogDescription>
                确定要删除选中的 {selectedIds.length} 个仓库吗？此操作无法撤销。
              </AlertDialogDescription>
            </AlertDialogHeader>
            <AlertDialogFooter>
              <AlertDialogCancel>取消</AlertDialogCancel>
              <AlertDialogAction
                onClick={handleBatchDelete}
                disabled={deleteWarehousesMutation.isPending}
                className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
              >
                {deleteWarehousesMutation.isPending ? '删除中...' : '确认删除'}
              </AlertDialogAction>
            </AlertDialogFooter>
          </AlertDialogContent>
        </AlertDialog>
      )}
    </div>
  );
}