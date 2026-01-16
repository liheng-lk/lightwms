'use client';

import { Pencil, Ban } from 'lucide-react';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import { Badge } from '@/components/ui/badge';
import { Checkbox } from '@/components/ui/checkbox';
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
import { useDeactivateWarehouse } from '@/lib/hooks/use-warehouses';
import type { Warehouse } from '@/lib/types';

interface WarehouseTableProps {
  warehouses: Warehouse[];
  isLoading?: boolean;
  onEdit?: (warehouse: Warehouse) => void;
  onDeactivateSuccess?: () => void;
  selectable?: boolean;
  selectedIds?: number[];
  onSelectionChange?: (ids: number[]) => void;
}

export function WarehouseTable({ 
  warehouses, 
  isLoading, 
  onEdit,
  onDeactivateSuccess,
  selectable = false,
  selectedIds = [],
  onSelectionChange,
}: WarehouseTableProps) {
  const { mutate: deactivateWarehouse, isPending: isDeactivating } = useDeactivateWarehouse();

  const handleDeactivate = (id: number) => {
    deactivateWarehouse(id, {
      onSuccess: () => {
        onDeactivateSuccess?.();
      },
    });
  };

  const handleSelectAll = (checked: boolean) => {
    if (!onSelectionChange) return;
    if (checked) {
      onSelectionChange(warehouses.map(w => w.id));
    } else {
      onSelectionChange([]);
    }
  };

  const handleSelectItem = (id: number, checked: boolean) => {
    if (!onSelectionChange) return;
    if (checked) {
      onSelectionChange([...selectedIds, id]);
    } else {
      onSelectionChange(selectedIds.filter(i => i !== id));
    }
  };

  const allSelected = warehouses.length > 0 && warehouses.every(w => selectedIds.includes(w.id));
  const someSelected = selectedIds.length > 0 && !allSelected;

  if (isLoading) {
    return <WarehouseTableSkeleton showCheckbox={selectable} />;
  }
  
  if (warehouses.length === 0) {
    return (
      <div className="text-center py-12 text-muted-foreground">
        暂无仓库数据
      </div>
    );
  }
  
  return (
    <div className="border rounded-lg overflow-hidden">
      <Table>
        <TableHeader>
          <TableRow>
            {selectable && (
              <TableHead className="w-[40px]">
                <Checkbox
                  checked={allSelected}
                  onCheckedChange={handleSelectAll}
                  aria-label="全选"
                  {...(someSelected ? { 'data-state': 'indeterminate' } : {})}
                />
              </TableHead>
            )}
            <TableHead className="w-[120px]">编码</TableHead>
            <TableHead>名称</TableHead>
            <TableHead className="hidden md:table-cell">描述</TableHead>
            <TableHead className="w-[80px]">状态</TableHead>
            <TableHead className="w-[120px]">操作</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {warehouses.map((warehouse) => {
            const isSelected = selectedIds.includes(warehouse.id);
            return (
            <TableRow key={warehouse.id} data-state={isSelected ? 'selected' : undefined}>
              {selectable && (
                <TableCell>
                  <Checkbox
                    checked={isSelected}
                    onCheckedChange={(checked) => handleSelectItem(warehouse.id, !!checked)}
                    aria-label={`选择 ${warehouse.name}`}
                  />
                </TableCell>
              )}
              <TableCell className="font-mono text-sm">
                {warehouse.code}
              </TableCell>
              <TableCell>{warehouse.name}</TableCell>
              <TableCell className="hidden md:table-cell text-muted-foreground">
                {warehouse.description || '-'}
              </TableCell>
              <TableCell>
                <Badge variant={warehouse.is_active ? 'default' : 'secondary'}>
                  {warehouse.is_active ? '启用' : '停用'}
                </Badge>
              </TableCell>
              <TableCell>
                <div className="flex items-center gap-1">
                  <Button
                    variant="ghost"
                    size="icon"
                    onClick={() => onEdit?.(warehouse)}
                    title="编辑仓库"
                  >
                    <Pencil className="h-4 w-4" />
                  </Button>
                  
                  {warehouse.is_active && (
                    <AlertDialog>
                      <AlertDialogTrigger asChild>
                        <Button
                          variant="ghost"
                          size="icon"
                          title="停用仓库"
                          disabled={isDeactivating}
                        >
                          <Ban className="h-4 w-4" />
                        </Button>
                      </AlertDialogTrigger>
                      <AlertDialogContent>
                        <AlertDialogHeader>
                          <AlertDialogTitle>确认停用仓库</AlertDialogTitle>
                          <AlertDialogDescription>
                            确定要停用仓库「{warehouse.name}」吗？停用后该仓库下的库位将无法使用。
                          </AlertDialogDescription>
                        </AlertDialogHeader>
                        <AlertDialogFooter>
                          <AlertDialogCancel>取消</AlertDialogCancel>
                          <AlertDialogAction
                            onClick={() => handleDeactivate(warehouse.id)}
                          >
                            确认停用
                          </AlertDialogAction>
                        </AlertDialogFooter>
                      </AlertDialogContent>
                    </AlertDialog>
                  )}
                </div>
              </TableCell>
            </TableRow>
          );
          })}
        </TableBody>
      </Table>
    </div>
  );
}

function WarehouseTableSkeleton({ showCheckbox }: { showCheckbox?: boolean }) {
  return (
    <div className="border rounded-lg overflow-hidden">
      <Table>
        <TableHeader>
          <TableRow>
            {showCheckbox && (
              <TableHead className="w-[40px]">
                <Skeleton className="h-4 w-4" />
              </TableHead>
            )}
            <TableHead className="w-[120px]">编码</TableHead>
            <TableHead>名称</TableHead>
            <TableHead className="hidden md:table-cell">描述</TableHead>
            <TableHead className="w-[80px]">状态</TableHead>
            <TableHead className="w-[120px]">操作</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {Array.from({ length: 5 }).map((_, i) => (
            <TableRow key={i}>
              {showCheckbox && (
                <TableCell><Skeleton className="h-4 w-4" /></TableCell>
              )}
              <TableCell><Skeleton className="h-4 w-16" /></TableCell>
              <TableCell><Skeleton className="h-4 w-24" /></TableCell>
              <TableCell className="hidden md:table-cell"><Skeleton className="h-4 w-32" /></TableCell>
              <TableCell><Skeleton className="h-5 w-12" /></TableCell>
              <TableCell><Skeleton className="h-8 w-16" /></TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}
