'use client';

import { useState, useCallback } from 'react';
import { LocationTree } from '@/components/trees/location-tree';
import { LocationForm } from '@/components/locations/location-form';
import { PageHelp } from '@/components/ui/help-tooltip';
import { useWarehouses } from '@/lib/hooks/use-trees';
import { useAuth } from '@/providers/auth-provider';
import { useQueryClient } from '@tanstack/react-query';
import type { Location } from '@/lib/types';

export default function LocationsPage() {
  const { user } = useAuth();
  const canManage = user?.role === 'super_admin' || user?.role === 'item_manager';
  const [showCreateDialog, setShowCreateDialog] = useState(false);
  const [editingLocation, setEditingLocation] = useState<Location | undefined>(undefined);
  const [selectedWarehouseId, setSelectedWarehouseId] = useState<number | undefined>(undefined);
  const [selectedParentId, setSelectedParentId] = useState<number | undefined>(undefined);
  const queryClient = useQueryClient();

  const { data: warehouses } = useWarehouses();

  const handleAddLocation = useCallback((warehouseId: number, parentId?: number) => {
    if (!canManage) return;
    setSelectedWarehouseId(warehouseId);
    setSelectedParentId(parentId);
    setEditingLocation(undefined);
    setShowCreateDialog(true);
  }, [canManage]);

  const handleEditLocation = useCallback((location: Location) => {
    if (!canManage) return;
    setEditingLocation(location);
    setSelectedWarehouseId(location.warehouse);
    setSelectedParentId(location.parent || undefined);
    setShowCreateDialog(true);
  }, [canManage]);

  const handleSuccess = useCallback(() => {
    queryClient.invalidateQueries({ queryKey: ['locations'] });
  }, [queryClient]);

  const handleDialogClose = useCallback((open: boolean) => {
    setShowCreateDialog(open);
    if (!open) {
      setSelectedWarehouseId(undefined);
      setSelectedParentId(undefined);
      setEditingLocation(undefined);
    }
  }, []);

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2">
        <h1 className="text-2xl font-semibold">库位管理</h1>
        <PageHelp
          title="库位管理使用指南"
          tips={[
            '库位用于标识物品的存放位置',
            '支持多级库位结构（仓库/区域/货架/层）',
            '先选择仓库，再查看或管理该仓库的库位',
            '点击库位名称可查看该位置的物品',
            '停用库位前需先移除或转移其下的物品',
            '物品管理员可维护全部有效库存库位；负责人字段用于责任标识，不作为权限隔离',
          ]}
        />
      </div>

      <p className="text-sm text-muted-foreground">
        选择仓库后可查看库位结构；物品管理员和超级管理员可维护全部有效库存库位
      </p>

      <LocationTree
        showManagement={canManage}
        onAddLocation={canManage ? handleAddLocation : undefined}
        onEditLocation={canManage ? handleEditLocation : undefined}
      />

      {canManage && (
        <LocationForm
          location={editingLocation}
          warehouses={warehouses || []}
          selectedWarehouseId={selectedWarehouseId}
          selectedParentId={selectedParentId}
          open={showCreateDialog}
          onOpenChange={handleDialogClose}
          onSuccess={handleSuccess}
        />
      )}
    </div>
  );
}
