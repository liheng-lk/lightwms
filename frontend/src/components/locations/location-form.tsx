'use client';

import { useEffect, useMemo } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from '@/components/ui/form';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { useCreateLocation, useUpdateLocation, useLocationTreeByWarehouse } from '@/lib/hooks/use-trees';
import { useUsers } from '@/lib/hooks/use-users';
import type { Location, Warehouse } from '@/lib/types';

// Form validation schema
const locationFormSchema = z.object({
  code: z.string().min(1, '请输入库位编码'),
  name: z.string().min(1, '请输入库位名称'),
  warehouse: z.number({ message: '请选择仓库' }),
  owner: z.number({ message: '请选择负责人' }),
  parent: z.number().nullable().optional(),
});

type LocationFormData = z.infer<typeof locationFormSchema>;

interface LocationFormProps {
  location?: Location;
  warehouses: Warehouse[];
  selectedWarehouseId?: number;
  selectedParentId?: number;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSuccess?: () => void;
}

// Helper function to flatten tree for parent selection
function flattenLocations(locations: Location[], level = 0): Array<Location & { level: number }> {
  const result: Array<Location & { level: number }> = [];
  for (const loc of locations) {
    result.push({ ...loc, level });
    if (loc.children && loc.children.length > 0) {
      result.push(...flattenLocations(loc.children, level + 1));
    }
  }
  return result;
}

export function LocationForm({ 
  location, 
  warehouses, 
  selectedWarehouseId,
  selectedParentId,
  open, 
  onOpenChange, 
  onSuccess 
}: LocationFormProps) {
  const isEditing = !!location;
  const { mutate: createLocation, isPending: isCreating } = useCreateLocation();
  const { mutate: updateLocation, isPending: isUpdating } = useUpdateLocation();
  const { data: usersData } = useUsers({ page: 1, page_size: 100 });
  
  const isPending = isCreating || isUpdating;

  // Filter active users for owner selection
  const activeUsers = useMemo(() => {
    return usersData?.results?.filter(u => u.is_active) || [];
  }, [usersData]);

  const form = useForm<LocationFormData>({
    resolver: zodResolver(locationFormSchema),
    defaultValues: {
      code: '',
      name: '',
      warehouse: selectedWarehouseId || undefined,
      owner: undefined,
      parent: null,
    },
  });

  const watchedWarehouse = form.watch('warehouse');
  
  // Fetch locations for the selected warehouse to populate parent dropdown
  const { data: warehouseLocations } = useLocationTreeByWarehouse(watchedWarehouse || null);
  
  // Flatten locations for parent selection, excluding current location and its children
  const availableParents = useMemo(() => {
    if (!warehouseLocations) return [];
    const flattened = flattenLocations(warehouseLocations);
    if (isEditing && location) {
      // Exclude current location and its descendants
      const excludeIds = new Set<number>();
      const collectIds = (loc: Location) => {
        excludeIds.add(loc.id);
        loc.children?.forEach(collectIds);
      };
      // Find current location in tree and collect its descendants
      const findAndCollect = (locs: Location[]) => {
        for (const loc of locs) {
          if (loc.id === location.id) {
            collectIds(loc);
            return;
          }
          if (loc.children) findAndCollect(loc.children);
        }
      };
      findAndCollect(warehouseLocations);
      return flattened.filter(loc => !excludeIds.has(loc.id));
    }
    return flattened;
  }, [warehouseLocations, isEditing, location]);

  // Reset form when dialog opens/closes or location changes
  useEffect(() => {
    if (open) {
      if (location) {
        // Tree nodes use warehouse_id, full location objects use warehouse
        const warehouseId = (location as unknown as { warehouse_id?: number }).warehouse_id || location.warehouse;
        // Tree nodes use owner_id, full location objects use owner
        const ownerId = (location as unknown as { owner_id?: number }).owner_id || location.owner;
        // Tree nodes use parent_id, full location objects use parent
        const parentId = (location as unknown as { parent_id?: number }).parent_id ?? location.parent;
        form.reset({
          code: location.code,
          name: location.name,
          warehouse: warehouseId,
          owner: ownerId,
          parent: parentId || null,
        });
      } else {
        form.reset({
          code: '',
          name: '',
          warehouse: selectedWarehouseId || undefined,
          owner: undefined,
          parent: selectedParentId || null,
        });
      }
    }
  }, [open, location, selectedWarehouseId, selectedParentId, form]);

  const onSubmit = (data: LocationFormData) => {
    if (isEditing && location) {
      // Update existing location - allow editing code, name, owner
      updateLocation(
        { id: location.id, data: { code: data.code, name: data.name, owner: data.owner } },
        {
          onSuccess: () => {
            form.reset();
            onOpenChange(false);
            onSuccess?.();
          },
        }
      );
    } else {
      // Create new location - Requirements 16.3, 16.4
      createLocation(
        {
          code: data.code,
          name: data.name,
          warehouse: data.warehouse,
          owner: data.owner,
          parent: data.parent || undefined,
        },
        {
          onSuccess: () => {
            form.reset();
            onOpenChange(false);
            onSuccess?.();
          },
        }
      );
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[425px]">
        <DialogHeader>
          <DialogTitle>{isEditing ? '编辑库位' : '新增库位'}</DialogTitle>
        </DialogHeader>

        <Form {...form}>
          <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
            {/* 仓库显示（编辑模式只读） */}
            {isEditing ? (
              <FormItem>
                <FormLabel>仓库</FormLabel>
                <Input 
                  value={(() => {
                    const warehouseId = (location as unknown as { warehouse_id?: number })?.warehouse_id || location?.warehouse;
                    const warehouse = warehouses.find(w => w.id === warehouseId);
                    return warehouse?.name || `仓库 #${warehouseId}`;
                  })()}
                  disabled
                  className="bg-muted"
                />
              </FormItem>
            ) : (
              <FormField
                control={form.control}
                name="warehouse"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>仓库 *</FormLabel>
                    <Select
                      value={field.value?.toString()}
                      onValueChange={(value) => {
                        field.onChange(Number(value));
                        // Reset parent when warehouse changes
                        form.setValue('parent', null);
                      }}
                    >
                      <FormControl>
                        <SelectTrigger className="w-full">
                          <SelectValue placeholder="请选择仓库" />
                        </SelectTrigger>
                      </FormControl>
                      <SelectContent>
                        {warehouses.filter(w => w.is_active).map((warehouse) => (
                          <SelectItem key={warehouse.id} value={warehouse.id.toString()}>
                            {warehouse.name} ({warehouse.code})
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                    <FormMessage />
                  </FormItem>
                )}
              />
            )}

            {/* 父级库位显示（编辑模式只读） */}
            {isEditing ? (
              <FormItem>
                <FormLabel>父级库位</FormLabel>
                <Input 
                  value={(() => {
                    const parentId = (location as unknown as { parent_id?: number })?.parent_id ?? location?.parent;
                    if (!parentId) return '无（顶级库位）';
                    const parent = availableParents.find(p => p.id === parentId);
                    return parent?.name || `库位 #${parentId}`;
                  })()}
                  disabled
                  className="bg-muted"
                />
              </FormItem>
            ) : (
              <FormField
                control={form.control}
                name="parent"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>父级库位</FormLabel>
                    <Select
                      value={field.value?.toString() || 'none'}
                      onValueChange={(value) => field.onChange(value === 'none' ? null : Number(value))}
                      disabled={!watchedWarehouse}
                    >
                      <FormControl>
                        <SelectTrigger className="w-full">
                          <SelectValue placeholder="无（顶级库位）" />
                        </SelectTrigger>
                      </FormControl>
                      <SelectContent>
                        <SelectItem value="none">无（顶级库位）</SelectItem>
                        {availableParents.map((loc) => (
                          <SelectItem key={loc.id} value={loc.id.toString()}>
                            {'　'.repeat(loc.level)}{loc.name} ({loc.code})
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                    <FormMessage />
                  </FormItem>
                )}
              />
            )}

            {/* 负责人选择 */}
            <FormField
              control={form.control}
              name="owner"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>负责人 *</FormLabel>
                  <Select
                    value={field.value?.toString()}
                    onValueChange={(value) => field.onChange(Number(value))}
                  >
                    <FormControl>
                      <SelectTrigger className="w-full">
                        <SelectValue placeholder="请选择负责人" />
                      </SelectTrigger>
                    </FormControl>
                    <SelectContent>
                      {activeUsers.map((user) => (
                        <SelectItem key={user.id} value={user.id.toString()}>
                          {user.username}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  <FormMessage />
                </FormItem>
              )}
            />

            {/* 编码 */}
            <FormField
              control={form.control}
              name="code"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>编码 *</FormLabel>
                  <FormControl>
                    <Input 
                      placeholder="例如：A-01-01" 
                      {...field} 
                    />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            {/* 名称 */}
            <FormField
              control={form.control}
              name="name"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>名称 *</FormLabel>
                  <FormControl>
                    <Input placeholder="例如：A区1排1层" {...field} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            <DialogFooter>
              <Button
                type="button"
                variant="outline"
                onClick={() => onOpenChange(false)}
              >
                取消
              </Button>
              <Button type="submit" disabled={isPending}>
                {isPending ? '提交中...' : isEditing ? '保存' : '创建'}
              </Button>
            </DialogFooter>
          </form>
        </Form>
      </DialogContent>
    </Dialog>
  );
}
