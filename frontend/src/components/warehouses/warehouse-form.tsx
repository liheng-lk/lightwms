'use client';

import { useEffect } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { Trash2 } from 'lucide-react';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from '@/components/ui/dialog';
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
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from '@/components/ui/form';
import { useCreateWarehouse, useUpdateWarehouse, useDeleteWarehouse } from '@/lib/hooks/use-warehouses';
import type { Warehouse } from '@/lib/types';

// Form validation schema
const warehouseFormSchema = z.object({
  code: z.string().min(1, '请输入仓库编码'),
  name: z.string().min(1, '请输入仓库名称'),
  description: z.string().optional(),
});

type WarehouseFormData = z.infer<typeof warehouseFormSchema>;

interface WarehouseFormProps {
  warehouse?: Warehouse;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSuccess?: () => void;
}

export function WarehouseForm({ warehouse, open, onOpenChange, onSuccess }: WarehouseFormProps) {
  const isEditing = !!warehouse;
  const { mutate: createWarehouse, isPending: isCreating } = useCreateWarehouse();
  const { mutate: updateWarehouse, isPending: isUpdating } = useUpdateWarehouse();
  const { mutate: deleteWarehouse, isPending: isDeleting } = useDeleteWarehouse();
  
  const isPending = isCreating || isUpdating || isDeleting;

  // Handle delete warehouse
  const handleDelete = () => {
    if (!warehouse) return;
    deleteWarehouse(warehouse.id, {
      onSuccess: () => {
        onOpenChange(false);
        onSuccess?.();
      },
    });
  };

  const form = useForm<WarehouseFormData>({
    resolver: zodResolver(warehouseFormSchema),
    defaultValues: {
      code: '',
      name: '',
      description: '',
    },
  });

  // Reset form when dialog opens/closes or warehouse changes
  useEffect(() => {
    if (open) {
      if (warehouse) {
        form.reset({
          code: warehouse.code,
          name: warehouse.name,
          description: warehouse.description || '',
        });
      } else {
        form.reset({
          code: '',
          name: '',
          description: '',
        });
      }
    }
  }, [open, warehouse, form]);

  const onSubmit = (data: WarehouseFormData) => {
    if (isEditing && warehouse) {
      // Update existing warehouse - Requirements 17.4
      updateWarehouse(
        { id: warehouse.id, data },
        {
          onSuccess: () => {
            form.reset();
            onOpenChange(false);
            onSuccess?.();
          },
        }
      );
    } else {
      // Create new warehouse - Requirements 17.2, 17.3
      createWarehouse(data, {
        onSuccess: () => {
          form.reset();
          onOpenChange(false);
          onSuccess?.();
        },
      });
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[425px]">
        <DialogHeader>
          <DialogTitle>{isEditing ? '编辑仓库' : '新增仓库'}</DialogTitle>
        </DialogHeader>

        <Form {...form}>
          <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
            {/* 编码 */}
            <FormField
              control={form.control}
              name="code"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>编码 *</FormLabel>
                  <FormControl>
                    <Input 
                      placeholder="例如：WH-001" 
                      {...field} 
                      disabled={isEditing}
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
                    <Input placeholder="例如：主仓库" {...field} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            {/* 描述 */}
            <FormField
              control={form.control}
              name="description"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>描述</FormLabel>
                  <FormControl>
                    <Textarea
                      placeholder="仓库描述信息"
                      className="resize-none"
                      rows={3}
                      {...field}
                    />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            <DialogFooter className="flex-col sm:flex-row gap-2">
              {isEditing && (
                <AlertDialog>
                  <AlertDialogTrigger asChild>
                    <Button
                      type="button"
                      variant="destructive"
                      disabled={isPending}
                      className="sm:mr-auto"
                    >
                      <Trash2 className="h-4 w-4 mr-2" />
                      删除
                    </Button>
                  </AlertDialogTrigger>
                  <AlertDialogContent>
                    <AlertDialogHeader>
                      <AlertDialogTitle>确认删除仓库？</AlertDialogTitle>
                      <AlertDialogDescription>
                        删除后仓库数据将被永久移除，此操作不可恢复。如果仓库下有库位，需要先删除库位。
                      </AlertDialogDescription>
                    </AlertDialogHeader>
                    <AlertDialogFooter>
                      <AlertDialogCancel>取消</AlertDialogCancel>
                      <AlertDialogAction onClick={handleDelete}>
                        确认删除
                      </AlertDialogAction>
                    </AlertDialogFooter>
                  </AlertDialogContent>
                </AlertDialog>
              )}
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
