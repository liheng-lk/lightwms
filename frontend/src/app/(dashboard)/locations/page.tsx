'use client';

import { useState, useCallback } from 'react';
import { LocationTree } from '@/components/trees/location-tree';
import { LocationForm } from '@/components/locations/location-form';
import { PageHelp } from '@/components/ui/help-tooltip';
import { useWarehouses } from '@/lib/hooks/use-trees';
import { useQueryClient } from '@tanstack/react-query';
import type { Location } from '@/lib/types';

export default function LocationsPage() {
  const [showCreateDialog, setShowCreateDialog] = useState(false);
  const [editingLocation, setEditingLocation] = useState<Location | undefined>(undefined);
  const [selectedWarehouseId, setSelectedWarehouseId] = useState<number | undefined>(undefined);
  const [selectedParentId, setSelectedParentId] = useState<number | undefined>(undefined);
  const queryClient = useQueryClient();
  
  const { data: warehouses } = useWarehouses();

  // Handler for adding a new location - Requirements 16.3, 16.4
  const handleAddLocation = useCallback((warehouseId: number, parentId?: number) => {
    setSelectedWarehouseId(warehouseId);
    setSelectedParentId(parentId);
    setEditingLocation(undefined);
    setShowCreateDialog(true);
  }, []);

  // Handler for editing a location
  const handleEditLocation = useCallback((location: Location) => {
    setEditingLocation(location);
    setSelectedWarehouseId(location.warehouse);
    setSelectedParentId(location.parent || undefined);
    setShowCreateDialog(true);
  }, []);

  // Handler for successful location creation/update
  const handleSuccess = useCallback(() => {
    // Invalidate location queries to refresh the tree
    queryClient.invalidateQueries({ queryKey: ['locations'] });
  }, [queryClient]);

  // Handler for dialog close
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
            '仅超级管理员可管理库位',
          ]}
        />
      </div>
      
      <p className="text-sm text-muted-foreground">
        选择仓库后可查看和管理该仓库的库位结构，点击库位可查看该库位下的物品
      </p>
      
      {/* Location Tree with management features - Requirements 16.1, 16.2 */}
      <LocationTree 
        showManagement={true}
        onAddLocation={handleAddLocation}
        onEditLocation={handleEditLocation}
      />

      {/* Create/Edit Location Dialog - Requirements 16.3, 16.4 */}
      <LocationForm
        location={editingLocation}
        warehouses={warehouses || []}
        selectedWarehouseId={selectedWarehouseId}
        selectedParentId={selectedParentId}
        open={showCreateDialog}
        onOpenChange={handleDialogClose}
        onSuccess={handleSuccess}
      />
    </div>
  );
}
