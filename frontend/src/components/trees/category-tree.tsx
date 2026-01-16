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
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { useCategoryTree, useDeactivateCategory } from '@/lib/hooks/use-trees';
import type { Category } from '@/lib/types';

interface CategoryTreeProps {
  selectedId?: number;
  showManagement?: boolean;
  onAddCategory?: (parentId?: number) => void;
  onEditCategory?: (category: Category) => void;
}

export function CategoryTree({ 
  selectedId, 
  showManagement = false, 
  onAddCategory,
  onEditCategory,
}: CategoryTreeProps) {
  const router = useRouter();
  const { data: categories, isLoading, refetch } = useCategoryTree();
  const { mutate: deactivateCategory, isPending: isDeactivating } = useDeactivateCategory();
  
  const handleNodeClick = (node: Category) => {
    router.push(`/items?category=${node.id}`);
  };

  const handleDeactivate = (id: number) => {
    deactivateCategory(id, {
      onSuccess: () => {
        refetch();
      },
    });
  };

  const handleAddChild = (parentId?: number) => {
    onAddCategory?.(parentId);
  };

  const handleEdit = (category: Category) => {
    onEditCategory?.(category);
  };
  
  if (isLoading) {
    return <TreeSkeleton />;
  }
  
  if (!categories || categories.length === 0) {
    return (
      <Card>
        <CardContent className="py-8">
          <div className="text-center text-muted-foreground">
            暂无分类数据
            {showManagement && (
              <div className="mt-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => handleAddChild()}
                >
                  <Plus className="h-4 w-4 mr-1" />
                  创建第一个分类
                </Button>
              </div>
            )}
          </div>
        </CardContent>
      </Card>
    );
  }
  
  return (
    <Card>
      <CardHeader className="py-3 flex flex-row items-center justify-between">
        <CardTitle className="text-base">分类结构</CardTitle>
        {showManagement && (
          <Button
            variant="outline"
            size="sm"
            onClick={() => handleAddChild()}
          >
            <Plus className="h-4 w-4 mr-1" />
            新增顶级分类
          </Button>
        )}
      </CardHeader>
      <CardContent className="pt-0">
        <CategoryTreeView
          nodes={categories}
          onNodeClick={handleNodeClick}
          selectedId={selectedId}
          showManagement={showManagement}
          onDeactivate={handleDeactivate}
          onAddChild={handleAddChild}
          onEdit={handleEdit}
          isDeactivating={isDeactivating}
        />
      </CardContent>
    </Card>
  );
}

interface CategoryTreeViewProps {
  nodes: Category[];
  onNodeClick?: (node: Category) => void;
  selectedId?: number;
  showManagement?: boolean;
  onDeactivate?: (id: number) => void;
  onAddChild?: (parentId?: number) => void;
  onEdit?: (category: Category) => void;
  isDeactivating?: boolean;
}

function CategoryTreeView({ 
  nodes, 
  onNodeClick, 
  selectedId, 
  showManagement,
  onDeactivate,
  onAddChild,
  onEdit,
  isDeactivating,
}: CategoryTreeViewProps) {
  return (
    <div className="space-y-1">
      {nodes.map((node) => (
        <CategoryNodeItem
          key={node.id}
          node={node}
          onNodeClick={onNodeClick}
          selectedId={selectedId}
          level={0}
          showManagement={showManagement}
          onDeactivate={onDeactivate}
          onAddChild={onAddChild}
          onEdit={onEdit}
          isDeactivating={isDeactivating}
        />
      ))}
    </div>
  );
}

interface CategoryNodeItemProps {
  node: Category;
  onNodeClick?: (node: Category) => void;
  selectedId?: number;
  level: number;
  showManagement?: boolean;
  onDeactivate?: (id: number) => void;
  onAddChild?: (parentId?: number) => void;
  onEdit?: (category: Category) => void;
  isDeactivating?: boolean;
}

function CategoryNodeItem({ 
  node, 
  onNodeClick, 
  selectedId, 
  level,
  showManagement,
  onDeactivate,
  onAddChild,
  onEdit,
  isDeactivating,
}: CategoryNodeItemProps) {
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

        {!node.is_active && (
          <Badge variant="secondary" className="text-xs ml-1">
            已停用
          </Badge>
        )}
        
        {/* Management buttons - Requirements 15.3, 15.4, 15.5 */}
        {showManagement && node.is_active && (
          <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity ml-2">
            {/* Add child category button */}
            <Button
              variant="ghost"
              size="icon"
              className="h-6 w-6"
              onClick={(e) => {
                e.stopPropagation();
                onAddChild?.(node.id);
              }}
              title="添加子分类"
            >
              <Plus className="h-3 w-3" />
            </Button>

            {/* Edit category button - Requirements 15.4 */}
            <Button
              variant="ghost"
              size="icon"
              className="h-6 w-6"
              onClick={(e) => {
                e.stopPropagation();
                onEdit?.(node);
              }}
              title="编辑分类"
            >
              <Pencil className="h-3 w-3" />
            </Button>
            
            {/* Deactivate category button - Requirements 15.5, 15.6 */}
            <AlertDialog>
              <AlertDialogTrigger asChild>
                <Button
                  variant="ghost"
                  size="icon"
                  className="h-6 w-6"
                  title="停用分类"
                  disabled={isDeactivating}
                  onClick={(e) => e.stopPropagation()}
                >
                  <Ban className="h-3 w-3" />
                </Button>
              </AlertDialogTrigger>
              <AlertDialogContent>
                <AlertDialogHeader>
                  <AlertDialogTitle>确认停用分类</AlertDialogTitle>
                  <AlertDialogDescription>
                    确定要停用分类「{node.name}」吗？
                    {hasChildren && '该分类下有子分类，停用后子分类也将无法使用。'}
                    停用后该分类下的物品需要转移到其他分类。
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
            <CategoryNodeItem
              key={child.id}
              node={child}
              onNodeClick={onNodeClick}
              selectedId={selectedId}
              level={level + 1}
              showManagement={showManagement}
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
    <Card>
      <CardHeader className="py-3">
        <Skeleton className="h-5 w-24" />
      </CardHeader>
      <CardContent className="pt-0 space-y-2">
        {Array.from({ length: 5 }).map((_, i) => (
          <div key={i} className="flex items-center gap-2 px-2">
            <Skeleton className="h-4 w-4" />
            <Skeleton className="h-4 flex-1" />
          </div>
        ))}
      </CardContent>
    </Card>
  );
}
