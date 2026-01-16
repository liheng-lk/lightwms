'use client';

import { useState } from 'react';
import { ChevronRight, ChevronDown } from 'lucide-react';
import { cn } from '@/lib/utils';

export interface TreeNode {
  id: number;
  name: string;
  code?: string;
  is_active: boolean;
  children?: TreeNode[];
}

interface TreeViewProps {
  nodes: TreeNode[];
  onNodeClick?: (node: TreeNode) => void;
  selectedId?: number;
}

export function TreeView({ nodes, onNodeClick, selectedId }: TreeViewProps) {
  return (
    <div className="space-y-1">
      {nodes.map((node) => (
        <TreeNodeItem
          key={node.id}
          node={node}
          onNodeClick={onNodeClick}
          selectedId={selectedId}
          level={0}
        />
      ))}
    </div>
  );
}

interface TreeNodeItemProps {
  node: TreeNode;
  onNodeClick?: (node: TreeNode) => void;
  selectedId?: number;
  level: number;
}

function TreeNodeItem({ node, onNodeClick, selectedId, level }: TreeNodeItemProps) {
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
          'flex items-center gap-1 px-2 py-1.5 rounded-md cursor-pointer transition-colors',
          isSelected
            ? 'bg-primary text-primary-foreground'
            : 'hover:bg-muted',
          !node.is_active && 'opacity-50'
        )}
        style={{ paddingLeft: `${level * 16 + 8}px` }}
        onClick={handleClick}
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
        
        <span className="flex-1 truncate">{node.name}</span>
        
        {node.code && (
          <span className={cn(
            'text-xs font-mono',
            isSelected ? 'text-primary-foreground/70' : 'text-muted-foreground'
          )}>
            {node.code}
          </span>
        )}
      </div>
      
      {hasChildren && expanded && (
        <div>
          {node.children!.map((child) => (
            <TreeNodeItem
              key={child.id}
              node={child}
              onNodeClick={onNodeClick}
              selectedId={selectedId}
              level={level + 1}
            />
          ))}
        </div>
      )}
    </div>
  );
}
