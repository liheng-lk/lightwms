'use client';

import { useState, useCallback } from 'react';
import { CategoryTree } from '@/components/trees/category-tree';
import { CategoryForm } from '@/components/categories/category-form';
import { PageHelp } from '@/components/ui/help-tooltip';
import { useQueryClient } from '@tanstack/react-query';
import type { Category } from '@/lib/types';

export default function CategoriesPage() {
  const [showCreateDialog, setShowCreateDialog] = useState(false);
  const [selectedParentId, setSelectedParentId] = useState<number | undefined>(undefined);
  const [editingCategory, setEditingCategory] = useState<Category | undefined>(undefined);
  const queryClient = useQueryClient();

  // Handler for adding a new category - Requirements 15.2, 15.3
  const handleAddCategory = useCallback((parentId?: number) => {
    setSelectedParentId(parentId);
    setEditingCategory(undefined);
    setShowCreateDialog(true);
  }, []);

  // Handler for editing a category - Requirements 15.4
  const handleEditCategory = useCallback((category: Category) => {
    setEditingCategory(category);
    setSelectedParentId(undefined);
    setShowCreateDialog(true);
  }, []);

  // Handler for successful category creation/update
  const handleSuccess = useCallback(() => {
    // Invalidate category queries to refresh the tree
    queryClient.invalidateQueries({ queryKey: ['categories'] });
  }, [queryClient]);

  // Handler for dialog close
  const handleDialogClose = useCallback((open: boolean) => {
    setShowCreateDialog(open);
    if (!open) {
      setSelectedParentId(undefined);
      setEditingCategory(undefined);
    }
  }, []);

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2">
        <h1 className="text-2xl font-semibold">分类管理</h1>
        <PageHelp
          title="分类管理使用指南"
          tips={[
            '分类用于组织和归类物品',
            '支持多级分类结构（父分类/子分类）',
            '点击分类名称可查看该分类下的物品',
            '停用分类前需先移除或转移其下的物品',
            '仅超级管理员可管理分类',
          ]}
        />
      </div>
      
      <p className="text-sm text-muted-foreground">
        管理物品分类结构，点击分类可查看该分类下的物品
      </p>
      
      {/* Category Tree with management features - Requirements 15.1 */}
      <CategoryTree 
        showManagement={true}
        onAddCategory={handleAddCategory}
        onEditCategory={handleEditCategory}
      />

      {/* Create/Edit Category Dialog - Requirements 15.2, 15.3, 15.4 */}
      <CategoryForm
        category={editingCategory}
        selectedParentId={selectedParentId}
        open={showCreateDialog}
        onOpenChange={handleDialogClose}
        onSuccess={handleSuccess}
      />
    </div>
  );
}
