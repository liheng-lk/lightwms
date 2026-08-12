'use client';

import { useState, useCallback } from 'react';
import { CategoryTree } from '@/components/trees/category-tree';
import { CategoryForm } from '@/components/categories/category-form';
import { PageHelp } from '@/components/ui/help-tooltip';
import { useAuth } from '@/providers/auth-provider';
import { useQueryClient } from '@tanstack/react-query';
import type { Category } from '@/lib/types';

export default function CategoriesPage() {
  const { user } = useAuth();
  const canManage = user?.role === 'super_admin' || user?.role === 'item_manager';
  const [showCreateDialog, setShowCreateDialog] = useState(false);
  const [selectedParentId, setSelectedParentId] = useState<number | undefined>(undefined);
  const [editingCategory, setEditingCategory] = useState<Category | undefined>(undefined);
  const queryClient = useQueryClient();

  const handleAddCategory = useCallback((parentId?: number) => {
    if (!canManage) return;
    setSelectedParentId(parentId);
    setEditingCategory(undefined);
    setShowCreateDialog(true);
  }, [canManage]);

  const handleEditCategory = useCallback((category: Category) => {
    if (!canManage) return;
    setEditingCategory(category);
    setSelectedParentId(undefined);
    setShowCreateDialog(true);
  }, [canManage]);

  const handleSuccess = useCallback(() => {
    queryClient.invalidateQueries({ queryKey: ['categories'] });
  }, [queryClient]);

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
            '物品管理员和超级管理员可维护有效分类，普通用户只读',
          ]}
        />
      </div>
      
      <p className="text-sm text-muted-foreground">
        管理物品分类结构，点击分类可查看该分类下的物品
      </p>
      
      <CategoryTree 
        showManagement={canManage}
        onAddCategory={canManage ? handleAddCategory : undefined}
        onEditCategory={canManage ? handleEditCategory : undefined}
      />

      {canManage && (
        <CategoryForm
          category={editingCategory}
          selectedParentId={selectedParentId}
          open={showCreateDialog}
          onOpenChange={handleDialogClose}
          onSuccess={handleSuccess}
        />
      )}
    </div>
  );
}