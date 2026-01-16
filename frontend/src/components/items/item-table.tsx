'use client';

import Link from 'next/link';
import Image from 'next/image';
import { Pencil, ImageIcon } from 'lucide-react';
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
import { Checkbox } from '@/components/ui/checkbox';
import {
  HoverCard,
  HoverCardContent,
  HoverCardTrigger,
} from '@/components/ui/hover-card';
import { StatusBadge, ItemTypeBadge } from '@/components/ui/status-badge';
import { usePermissions } from '@/lib/hooks/use-permissions';
import type { Item } from '@/lib/types';

// Convert backend image URL to frontend proxy URL
function toProxyUrl(url: string | undefined | null): string {
  if (!url) return '';
  if (url.startsWith('/media/')) {
    return `/api/media${url.replace('/media', '')}`;
  }
  const mediaMatch = url.match(/\/media\/(.+)$/);
  if (mediaMatch) {
    return `/api/media/${mediaMatch[1]}`;
  }
  if (!url.startsWith('http') && !url.startsWith('/')) {
    return `/api/media/${url}`;
  }
  return url;
}

interface ItemThumbnailProps {
  item: Item;
}

function ItemThumbnail({ item }: ItemThumbnailProps) {
  const thumbUrl = item.primary_image?.thumb_256_url;
  const largeUrl = item.primary_image?.thumb_768_url;
  
  if (!thumbUrl) {
    return (
      <div className="w-10 h-10 rounded bg-muted flex items-center justify-center">
        <ImageIcon className="h-4 w-4 text-muted-foreground" />
      </div>
    );
  }
  
  return (
    <HoverCard openDelay={200} closeDelay={100}>
      <HoverCardTrigger asChild>
        <div className="w-10 h-10 rounded overflow-hidden bg-muted cursor-pointer relative">
          <Image
            src={toProxyUrl(thumbUrl)}
            alt={item.name}
            fill
            className="object-cover"
            sizes="40px"
          />
        </div>
      </HoverCardTrigger>
      <HoverCardContent side="right" className="w-64 p-2">
        <div className="relative aspect-square w-full rounded overflow-hidden bg-muted">
          <Image
            src={toProxyUrl(largeUrl || thumbUrl)}
            alt={item.name}
            fill
            className="object-contain"
            sizes="256px"
          />
        </div>
        <p className="text-sm text-center mt-2 text-muted-foreground truncate">
          {item.name}
        </p>
      </HoverCardContent>
    </HoverCard>
  );
}

interface ItemTableProps {
  items: Item[];
  isLoading?: boolean;
  onEdit?: (item: Item) => void;
  onDeactivate?: (item: Item) => void;
  selectable?: boolean;
  selectedIds?: number[];
  onSelectionChange?: (ids: number[]) => void;
}

export function ItemTable({ 
  items, 
  isLoading, 
  onEdit,
  onDeactivate,
  selectable = false,
  selectedIds = [],
  onSelectionChange,
}: ItemTableProps) {
  const { canEdit } = usePermissions();
  
  const showActionsColumn = !!onEdit || !!onDeactivate;
  
  const handleSelectAll = (checked: boolean | 'indeterminate') => {
    if (!onSelectionChange) return;
    // checked is the NEW state after clicking
    // true = user wants to select all
    // false = user wants to deselect all
    if (checked) {
      onSelectionChange(items.map(item => item.id));
    } else {
      onSelectionChange([]);
    }
  };
  
  const handleSelectItem = (itemId: number, checked: boolean) => {
    if (!onSelectionChange) return;
    if (checked) {
      onSelectionChange([...selectedIds, itemId]);
    } else {
      onSelectionChange(selectedIds.filter(id => id !== itemId));
    }
  };
  
  const allSelected = items.length > 0 && items.every(item => selectedIds.includes(item.id));
  const someSelected = selectedIds.length > 0 && !allSelected;

  if (isLoading) {
    return <ItemTableSkeleton showActions={showActionsColumn} showCheckbox={selectable} />;
  }
  
  if (items.length === 0) {
    return (
      <div className="text-center py-12 text-muted-foreground">
        暂无物品数据
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
                  checked={someSelected ? 'indeterminate' : allSelected}
                  onCheckedChange={handleSelectAll}
                  aria-label="全选"
                />
              </TableHead>
            )}
            <TableHead className="w-[60px]">图片</TableHead>
            <TableHead>名称</TableHead>
            <TableHead className="w-[100px]">类型</TableHead>
            <TableHead className="w-[100px]">状态</TableHead>
            <TableHead className="hidden md:table-cell">分类</TableHead>
            <TableHead className="hidden md:table-cell">库位</TableHead>
            <TableHead className="hidden lg:table-cell w-[100px]">数量</TableHead>
            <TableHead className="hidden lg:table-cell">负责人</TableHead>
            {showActionsColumn && (
              <TableHead className="w-[80px]">操作</TableHead>
            )}
          </TableRow>
        </TableHeader>
        <TableBody>
          {items.map((item) => {
            const canEditItem = canEdit({ owner_id: item.owner, owner: { id: item.owner } });
            const hasBarcode = !!item.barcode;
            const isSelected = selectedIds.includes(item.id);
            const itemType = item.item_type ?? item.type;
            
            // Calculate display status for reusable items
            const getDisplayStatus = () => {
              if (itemType === 'reusable') {
                const availableQty = item.available_quantity ?? item.quantity ?? 1;
                if (availableQty === 0) {
                  return 'unavailable';
                }
              }
              return item.status;
            };
            const displayStatus = getDisplayStatus();
            
            // Format quantity display
            const getQuantityDisplay = () => {
              if (itemType === 'consumable') {
                return String(item.quantity ?? 0);
              }
              if (itemType === 'reusable') {
                const total = item.quantity ?? 1;
                const available = item.available_quantity ?? total;
                // Always show quantity for reusable items
                return `${available}/${total}`;
              }
              return '-';
            };
            
            return (
              <TableRow key={item.id} data-state={isSelected ? 'selected' : undefined}>
                {selectable && (
                  <TableCell>
                    <Checkbox
                      checked={isSelected}
                      onCheckedChange={(checked) => handleSelectItem(item.id, !!checked)}
                      aria-label={`选择 ${item.name}`}
                    />
                  </TableCell>
                )}
                <TableCell>
                  <ItemThumbnail item={item} />
                </TableCell>
                <TableCell>
                  <Link 
                    href={`/items/${item.id}`}
                    className="hover:underline"
                  >
                    {item.name}
                  </Link>
                  {item.barcode && (
                    <div className="text-xs text-muted-foreground font-mono">
                      {item.barcode}
                    </div>
                  )}
                </TableCell>
                <TableCell>
                  <ItemTypeBadge itemType={itemType} />
                </TableCell>
                <TableCell>
                  <StatusBadge status={displayStatus} type="item" />
                </TableCell>
                <TableCell className="hidden md:table-cell text-muted-foreground">
                  {item.category_name || '-'}
                </TableCell>
                <TableCell className="hidden md:table-cell text-muted-foreground">
                  {item.location_full_path || item.location_name || '-'}
                </TableCell>
                <TableCell className="hidden lg:table-cell">
                  {getQuantityDisplay()}
                </TableCell>
                <TableCell className="hidden lg:table-cell text-muted-foreground">
                  {item.owner_username || '-'}
                </TableCell>
                {showActionsColumn && (
                  <TableCell>
                    {canEditItem && (
                      <Button
                        variant="ghost"
                        size="icon"
                        onClick={() => onEdit?.(item)}
                        title="编辑物品"
                      >
                        <Pencil className="h-4 w-4" />
                      </Button>
                    )}
                  </TableCell>
                )}
              </TableRow>
            );
          })}
        </TableBody>
      </Table>
    </div>
  );
}

interface ItemTableSkeletonProps {
  showActions?: boolean;
  showCheckbox?: boolean;
}

function ItemTableSkeleton({ showActions, showCheckbox }: ItemTableSkeletonProps) {
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
            <TableHead className="w-[60px]">图片</TableHead>
            <TableHead>名称</TableHead>
            <TableHead className="w-[100px]">类型</TableHead>
            <TableHead className="w-[100px]">状态</TableHead>
            <TableHead className="hidden md:table-cell">分类</TableHead>
            <TableHead className="hidden md:table-cell">库位</TableHead>
            <TableHead className="hidden lg:table-cell w-[100px]">数量</TableHead>
            <TableHead className="hidden lg:table-cell">负责人</TableHead>
            {showActions && (
              <TableHead className="w-[80px]">操作</TableHead>
            )}
          </TableRow>
        </TableHeader>
        <TableBody>
          {Array.from({ length: 10 }).map((_, i) => (
            <TableRow key={i}>
              {showCheckbox && (
                <TableCell><Skeleton className="h-4 w-4" /></TableCell>
              )}
              <TableCell><Skeleton className="h-10 w-10 rounded" /></TableCell>
              <TableCell><Skeleton className="h-4 w-32" /></TableCell>
              <TableCell><Skeleton className="h-5 w-16" /></TableCell>
              <TableCell><Skeleton className="h-5 w-14" /></TableCell>
              <TableCell className="hidden md:table-cell"><Skeleton className="h-4 w-16" /></TableCell>
              <TableCell className="hidden md:table-cell"><Skeleton className="h-4 w-16" /></TableCell>
              <TableCell className="hidden lg:table-cell"><Skeleton className="h-4 w-8" /></TableCell>
              <TableCell className="hidden lg:table-cell"><Skeleton className="h-4 w-16" /></TableCell>
              {showActions && (
                <TableCell><Skeleton className="h-8 w-8" /></TableCell>
              )}
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}
