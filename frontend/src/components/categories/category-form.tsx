'use client';

import { useEffect, useMemo, useState } from 'react';
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
import { useCreateCategory, useUpdateCategory, useCategoryTree, useDeleteCategory } from '@/lib/hooks/use-trees';
import type { Category } from '@/lib/types';

// Form validation schema
const categoryFormSchema = z.object({
  name: z.string().min(1, '请输入分类名称'),
  parent: z.number().nullable().optional(),
});

type CategoryFormData = z.infer<typeof categoryFormSchema>;

interface CategoryFormProps {
  category?: Category;
  selectedParentId?: number;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSuccess?: () => void;
}

// Helper function to flatten tree for parent selection
function flattenCategories(categories: Category[], level = 0): Array<Category & { level: number }> {
  const result: Array<Category & { level: number }> = [];
  for (const cat of categories) {
    result.push({ ...cat, level });
    if (cat.children && cat.children.length > 0) {
      result.push(...flattenCategories(cat.children, level + 1));
    }
  }
  return result;
}

export function CategoryForm({ 
  category, 
  selectedParentId,
  open, 
  onOpenChange, 
  onSuccess 
}: CategoryFormProps) {
  const isEditing = !!category;
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const { mutate: createCategory, isPending: isCreating } = useCreateCategory();
  const { mutate: updateCategory, isPending: isUpdating } = useUpdateCategory();
  const { mutate: deleteCategory, isPending: isDeleting } = useDeleteCategory();
  const { data: categoryTree } = useCategoryTree();
  
  const isPending = isCreating || isUpdating || isDeleting;

  const form = useForm<CategoryFormData>({
    resolver: zodResolver(categoryFormSchema),
    defaultValues: {
      name: '',
      parent: null,
    },
  });

  // Flatten categories for parent selection, excluding current category and its children
  const availableParents = useMemo(() => {
    if (!categoryTree) return [];
    const flattened = flattenCategories(categoryTree);
    if (isEditing && category) {
      // Exclude current category and its descendants
      const excludeIds = new Set<number>();
      const collectIds = (cat: Category) => {
        excludeIds.add(cat.id);
        cat.children?.forEach(collectIds);
      };
      // Find current category in tree and collect its descendants
      const findAndCollect = (cats: Category[]) => {
        for (const cat of cats) {
          if (cat.id === category.id) {
            collectIds(cat);
            return;
          }
          if (cat.children) findAndCollect(cat.children);
        }
      };
      findAndCollect(categoryTree);
      return flattened.filter(cat => !excludeIds.has(cat.id));
    }
    return flattened;
  }, [categoryTree, isEditing, category]);

  // Reset form when dialog opens/closes or category changes
  useEffect(() => {
    if (open) {
      if (category) {
        form.reset({
          name: category.name,
          parent: category.parent || null,
        });
      } else {
        form.reset({
          name: '',
          parent: selectedParentId || null,
        });
      }
    }
  }, [open, category, selectedParentId, form]);

  const onSubmit = (data: CategoryFormData) => {
    if (isEditing && category) {
      // Update existing category - Requirements 15.4
      updateCategory(
        { id: category.id, data: { name: data.name } },
        {
          onSuccess: () => {
            form.reset();
            onOpenChange(false);
            onSuccess?.();
          },
        }
      );
    } else {
      // Create new category - Requirements 15.2, 15.3
      createCategory(
        {
          name: data.name,
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

  const handleDelete = () => {
    if (!category) return;
    deleteCategory(category.id, {
      onSuccess: () => {
        setShowDeleteConfirm(false);
        onOpenChange(false);
        onSuccess?.();
      },
    });
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[425px]">
        <DialogHeader>
          <DialogTitle>{isEditing ? '编辑分类' : '新增分类'}</DialogTitle>
        </DialogHeader>

        <Form {...form}>
          <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
            {/* 父级分类选择 - Requirements 15.2 */}
            <FormField
              control={form.control}
              name="parent"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>父级分类</FormLabel>
                  <Select
                    value={field.value?.toString() || 'none'}
                    onValueChange={(value) => field.onChange(value === 'none' ? null : Number(value))}
                    disabled={isEditing}
                  >
                    <FormControl>
                      <SelectTrigger className="w-full">
                        <SelectValue placeholder="无（顶级分类）" />
                      </SelectTrigger>
                    </FormControl>
                    <SelectContent>
                      <SelectItem value="none">无（顶级分类）</SelectItem>
                      {availableParents.filter(cat => cat.is_active).map((cat) => (
                        <SelectItem key={cat.id} value={cat.id.toString()}>
                          {'　'.repeat(cat.level)}{cat.name}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
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
                    <Input placeholder="例如：电子设备" {...field} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            <DialogFooter className="flex justify-between">
              <div>
                {isEditing && (
                  <Button
                    type="button"
                    variant="destructive"
                    onClick={() => setShowDeleteConfirm(true)}
                    disabled={isPending}
                  >
                    删除
                  </Button>
                )}
              </div>
              <div className="flex gap-2">
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
              </div>
            </DialogFooter>
          </form>
        </Form>
      </DialogContent>

      {/* Delete confirmation dialog */}
      <AlertDialog open={showDeleteConfirm} onOpenChange={setShowDeleteConfirm}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>确认删除</AlertDialogTitle>
            <AlertDialogDescription asChild>
              <div className="space-y-2">
                <p>确定要永久删除分类 &quot;{category?.name}&quot; 吗？此操作无法撤销。</p>
                {category?.children && category.children.length > 0 && (
                  <p className="text-destructive font-medium">
                    ⚠️ 该分类下有 {category.children.length} 个子分类，请先删除子分类后再删除此分类。
                  </p>
                )}
              </div>
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>取消</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleDelete}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
              disabled={category?.children && category.children.length > 0}
            >
              {isDeleting ? '删除中...' : '确认删除'}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </Dialog>
  );
}
