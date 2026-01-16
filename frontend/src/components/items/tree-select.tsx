'use client';

import { useState, useMemo } from 'react';
import { ChevronRight, ChevronDown, Check } from 'lucide-react';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from '@/components/ui/popover';
import { Skeleton } from '@/components/ui/skeleton';
import { ScrollArea } from '@/components/ui/scroll-area';

export interface TreeNode {
  id: number;
  name: string;
  code?: string;
  is_active: boolean;
  children?: TreeNode[];
  warehouse?: number;
}

interface TreeSelectProps {
  nodes: TreeNode[];
  value?: number;
  onChange: (value: number | undefined) => void;
  placeholder?: string;
  loading?: boolean;
  showCode?: boolean;
  disabled?: boolean;
}

export function TreeSelect({
  nodes,
  value,
  onChange,
  placeholder = '请选择',
  loading = false,
  showCode = false,
  disabled = false,
}: TreeSelectProps) {
  const [open, setOpen] = useState(false);
  const [expandedIds, setExpandedIds] = useState<Set<number>>(new Set());

  // Find selected node label
  const selectedLabel = useMemo(() => {
    const findNode = (nodes: TreeNode[]): TreeNode | undefined => {
      for (const node of nodes) {
        if (node.id === value) return node;
        if (node.children) {
          const found = findNode(node.children);
          if (found) return found;
        }
      }
      return undefined;
    };
    const node = findNode(nodes);
    if (!node) return undefined;
    return showCode && node.code ? `${node.name} (${node.code})` : node.name;
  }, [nodes, value, showCode]);

  const toggleExpand = (id: number, e: React.MouseEvent) => {
    e.stopPropagation();
    setExpandedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  };

  const handleSelect = (node: TreeNode) => {
    if (!node.is_active) return;
    onChange(node.id);
    setOpen(false);
  };

  const renderNode = (node: TreeNode, level: number = 0) => {
    const hasChildren = node.children && node.children.length > 0;
    const isExpanded = expandedIds.has(node.id);
    const isSelected = value === node.id;

    return (
      <div key={node.id}>
        <div
          className={cn(
            'flex items-center gap-1 px-2 py-1.5 rounded-md cursor-pointer transition-colors',
            isSelected && 'bg-primary text-primary-foreground',
            !isSelected && node.is_active && 'hover:bg-muted',
            !node.is_active && 'opacity-50 cursor-not-allowed'
          )}
          style={{ paddingLeft: `${level * 16 + 8}px` }}
          onClick={() => handleSelect(node)}
        >
          {hasChildren ? (
            <button
              type="button"
              onClick={(e) => toggleExpand(node.id, e)}
              className="p-0.5 hover:bg-black/10 rounded"
            >
              {isExpanded ? (
                <ChevronDown className="h-4 w-4" />
              ) : (
                <ChevronRight className="h-4 w-4" />
              )}
            </button>
          ) : (
            <span className="w-5" />
          )}

          <span className="flex-1 truncate">{node.name}</span>

          {showCode && node.code && (
            <span
              className={cn(
                'text-xs font-mono',
                isSelected ? 'text-primary-foreground/70' : 'text-muted-foreground'
              )}
            >
              {node.code}
            </span>
          )}

          {isSelected && <Check className="h-4 w-4 ml-1" />}
        </div>

        {hasChildren && isExpanded && (
          <div>
            {node.children!.map((child) => renderNode(child, level + 1))}
          </div>
        )}
      </div>
    );
  };

  if (loading) {
    return <Skeleton className="h-9 w-full" />;
  }

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <Button
          variant="outline"
          role="combobox"
          aria-expanded={open}
          className="w-full justify-between font-normal"
          disabled={disabled}
        >
          <span className={cn(!selectedLabel && 'text-muted-foreground')}>
            {selectedLabel || placeholder}
          </span>
          <ChevronDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
        </Button>
      </PopoverTrigger>
      <PopoverContent className="w-[300px] p-0" align="start">
        <ScrollArea className="h-[300px]">
          <div className="p-2">
            {nodes.length === 0 ? (
              <div className="text-center py-4 text-muted-foreground text-sm">
                暂无数据
              </div>
            ) : (
              nodes.map((node) => renderNode(node))
            )}
          </div>
        </ScrollArea>
      </PopoverContent>
    </Popover>
  );
}
