'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { ChevronRight, ChevronDown, Ban, Plus, Pencil } from 'lucide-react';
import { cn } from '@/lib/utils';
import { Skeleton } from '@/components/ui/skeleton';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from '@/components/ui/alert-dialog';
import { useLocationTreeByWarehouse, useWarehouses, useDeactivateLocation } from '@/lib/hooks/use-trees';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import type { Location, Warehouse } from '@/lib/types';

interface LocationTreeProps {
  selectedId?: number;
  showManagement?: boolean;
  onAddLocation?: (warehouseId: number, parentId?: number) => void;
  onEditLocation?: (location: Location) => void;
}

export function LocationTree({ selectedId, showManagement = false, onAddLocation, onEditLocation }: LocationTreeProps) {
  const router = useRouter();
  const [selectedWarehouseId, setSelectedWarehouseId] = useState<number | null>(null);
  const { data: warehouses, isLoading: warehousesLoading } = useWarehouses();
  const { data: locations, isLoading: locationsLoading, refetch } = useLocationTreeByWarehouse(selectedWarehouseId);
  const { mutate: deactivateLocation, isPending: isDeactivating } = useDeactivateLocation();
  
  const handleNodeClick = (node: Location) => {
    router.push(`/items?location=${node.id}`);
  };

  const handleDeactivate = (id: number) => {
    deactivateLocation(id, {
      onSuccess: () => {
        refetch();
      },
    });
  };

  const handleAddChild = (warehouseId: number, parentId?: number) => {
    onAddLocation?.(warehouseId, parentId);
  };
  
  if (warehousesLoading) {
    return <TreeSkeleton />;
  }
  
  if (!warehouses || warehouses.length === 0) {
    return (
      <div className="text-center py-8 text-muted-foreground">
        暂无仓库数据，请先创建仓库
      </div>
    );
  }

  // Filter active warehouses
  const activeWarehouses = warehouses.filter(w => w.is_active);
  
  return (
    <div className="space-y-4">
      {/* Warehouse Selector - Requirements 16.1 */}
      <div className="flex items-center gap-4">
        <label className="text-sm font-medium">选择仓库：</label>
        <Select
          value={selectedWarehouseId?.toString() || ''}
          onValueChange={(value) => setSelectedWarehouseId(value ? Number(value) : null)}
        >
          <SelectTrigger className="w-[240px]">
            <SelectValue placeholder="请选择仓库" />
          </SelectTrigger>
          <SelectContent>
            {activeWarehouses.map((warehouse) => (
              <SelectItem key={warehouse.id} value={warehouse.id.toString()}>
                {warehouse.name} ({warehouse.code})
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        
        {showManagement && selectedWarehouseId && (
          <Button
            variant="outline"
            size="sm"
            onClick={() => handleAddChild(selectedWarehouseId)}
          >
            <Plus className="h-4 w-4 mr-1" />
            新增顶级库位
          </Button>
        )}
      </div>

      {/* Location Tree - Requirements 16.2 */}
      {selectedWarehouseId ? (
        locationsLoading ? (
          <TreeSkeleton />
        ) : !locations || locations.length === 0 ? (
          <Card>
            <CardContent className="py-8">
              <div className="text-center text-muted-foreground">
                该仓库暂无库位数据
                {showManagement && (
                  <div className="mt-2">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => handleAddChild(selectedWarehouseId)}
                    >
                      <Plus className="h-4 w-4 mr-1" />
                      创建第一个库位
                    </Button>
                  </div>
                )}
              </div>
            </CardContent>
          </Card>
        ) : (
          <Card>
            <CardHeader className="py-3">
              <CardTitle className="text-base">
                {activeWarehouses.find(w => w.id === selectedWarehouseId)?.name || '库位结构'}
              </CardTitle>
            </CardHeader>
            <CardContent className="pt-0">
              <LocationTreeView
                nodes={locations}
                onNodeClick={handleNodeClick}
                selectedId={selectedId}
                showManagement={showManagement}
                warehouseId={selectedWarehouseId}
                onDeactivate={handleDeactivate}
                onAddChild={handleAddChild}
                onEdit={onEditLocation}
                isDeactivating={isDeactivating}
              />
            </CardContent>
          </Card>
        )
      ) : (
        <Card>
          <CardContent className="py-8">
            <div className="text-center text-muted-foreground">
              请先选择一个仓库查看库位结构
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

interface LocationTreeViewProps {
  nodes: Location[];
  onNodeClick?: (node: Location) => void;
  selectedId?: number;
  showManagement?: boolean;
  warehouseId: number;
  onDeactivate?: (id: number) => void;
  onAddChild?: (warehouseId: number, parentId?: number) => void;
  onEdit?: (location: Location) => void;
  isDeactivating?: boolean;
}

function LocationTreeView({ 
  nodes, 
  onNodeClick, 
  selectedId, 
  showManagement,
  warehouseId,
  onDeactivate,
  onAddChild,
  onEdit,
  isDeactivating,
}: LocationTreeViewProps) {
  return (
    <div className="space-y-1">
      {nodes.map((node) => (
        <LocationNodeItem
          key={node.id}
          node={node}
          onNodeClick={onNodeClick}
          selectedId={selectedId}
          level={0}
          showManagement={showManagement}
          warehouseId={warehouseId}
          onDeactivate={onDeactivate}
          onAddChild={onAddChild}
          onEdit={onEdit}
          isDeactivating={isDeactivating}
        />
      ))}
    </div>
  );
}

interface LocationNodeItemProps {
  node: Location;
  onNodeClick?: (node: Location) => void;
  selectedId?: number;
  level: number;
  showManagement?: boolean;
  warehouseId: number;
  onDeactivate?: (id: number) => void;
  onAddChild?: (warehouseId: number, parentId?: number) => void;
  onEdit?: (location: Location) => void;
  isDeactivating?: boolean;
}

function LocationNodeItem({ 
  node, 
  onNodeClick, 
  selectedId, 
  level,
  showManagement,
  warehouseId,
  onDeactivate,
  onAddChild,
  onEdit,
  isDeactivating,
}: LocationNodeItemProps) {
  const [expanded, setExpanded] = useState(level < 1);
  const hasChildren = node.children && node.children.length > 0;
  const isSelected = selectedId === node.id;
  
  const handleToggle = (e: React.MouseEvent) => {
    e.stopPropagation();
    setExpanded(!expanded);
  };
  
  const handleClick = () => {
    onNodeClick?.(node);
  };
  
  return (
    <div>
      <div
        className={cn(
          'flex items-center gap-1 px-2 py-1.5 rounded-md transition-colors group',
          isSelected
            ? 'bg-primary text-primary-foreground'
            : 'hover:bg-muted',
          !node.is_active && 'opacity-50'
        )}
        style={{ paddingLeft: `${level * 16 + 8}px` }}
      >
        {hasChildren ? (
          <button
            onClick={handleToggle}
            className="p-0.5 hover:bg-black/10 rounded"
          >
            {expanded ? (
              <ChevronDown className="h-4 w-4" />
            ) : (
              <ChevronRight className="h-4 w-4" />
            )}
          </button>
        ) : (
          <span className="w-5" />
        )}
        
        <span 
          className="flex-1 truncate cursor-pointer"
          onClick={handleClick}
        >
          {node.name}
        </span>
        
        {/* 显示负责人 */}
        {node.owner_name && (
          <span className={cn(
            'text-xs',
            isSelected ? 'text-primary-foreground/70' : 'text-muted-foreground'
          )}>
            [{node.owner_name}]
          </span>
        )}
        
        <span className={cn(
          'text-xs font-mono',
          isSelected ? 'text-primary-foreground/70' : 'text-muted-foreground'
        )}>
          {node.code}
        </span>

        {!node.is_active && (
          <Badge variant="secondary" className="text-xs ml-1">
            已停用
          </Badge>
        )}
        
        {/* Management buttons - Requirements 16.3, 16.5 */}
        {showManagement && node.is_active && (
          <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity ml-2">
            <Button
              variant="ghost"
              size="icon"
              className="h-6 w-6"
              onClick={(e) => {
                e.stopPropagation();
                onEdit?.(node);
              }}
              title="编辑库位"
            >
              <Pencil className="h-3 w-3" />
            </Button>
            
            <Button
              variant="ghost"
              size="icon"
              className="h-6 w-6"
              onClick={(e) => {
                e.stopPropagation();
                onAddChild?.(warehouseId, node.id);
              }}
              title="添加子库位"
            >
              <Plus className="h-3 w-3" />
            </Button>
            
            <AlertDialog>
              <AlertDialogTrigger asChild>
                <Button
                  variant="ghost"
                  size="icon"
                  className="h-6 w-6"
                  title="停用库位"
                  disabled={isDeactivating}
                  onClick={(e) => e.stopPropagation()}
                >
                  <Ban className="h-3 w-3" />
                </Button>
              </AlertDialogTrigger>
              <AlertDialogContent>
                <AlertDialogHeader>
                  <AlertDialogTitle>确认停用库位</AlertDialogTitle>
                  <AlertDialogDescription>
                    确定要停用库位「{node.name}」吗？
                    {hasChildren && '该库位下有子库位，停用后子库位也将无法使用。'}
                    停用后该库位下的物品需要转移到其他库位。
                  </AlertDialogDescription>
                </AlertDialogHeader>
                <AlertDialogFooter>
                  <AlertDialogCancel>取消</AlertDialogCancel>
                  <AlertDialogAction
                    onClick={() => onDeactivate?.(node.id)}
                  >
                    确认停用
                  </AlertDialogAction>
                </AlertDialogFooter>
              </AlertDialogContent>
            </AlertDialog>
          </div>
        )}
      </div>
      
      {hasChildren && expanded && (
        <div>
          {node.children!.map((child) => (
            <LocationNodeItem
              key={child.id}
              node={child}
              onNodeClick={onNodeClick}
              selectedId={selectedId}
              level={level + 1}
              showManagement={showManagement}
              warehouseId={warehouseId}
              onDeactivate={onDeactivate}
              onAddChild={onAddChild}
              onEdit={onEdit}
              isDeactivating={isDeactivating}
            />
          ))}
        </div>
      )}
    </div>
  );
}

function TreeSkeleton() {
  return (
    <div className="space-y-4">
      <div className="flex items-center gap-4">
        <Skeleton className="h-4 w-20" />
        <Skeleton className="h-9 w-[240px]" />
      </div>
      <Card>
        <CardHeader className="py-3">
          <Skeleton className="h-5 w-24" />
        </CardHeader>
        <CardContent className="pt-0 space-y-2">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="flex items-center gap-2 px-2">
              <Skeleton className="h-4 w-4" />
              <Skeleton className="h-4 flex-1" />
            </div>
          ))}
        </CardContent>
      </Card>
    </div>
  );
}
