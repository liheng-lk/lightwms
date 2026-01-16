'use client';

import { StatusBadge, ItemTypeBadge } from '@/components/ui/status-badge';
import { Separator } from '@/components/ui/separator';
import { Badge } from '@/components/ui/badge';
import { User, Calendar, MapPin, FolderTree, Package } from 'lucide-react';
import type { Item } from '@/lib/types';

interface ItemInfoProps {
  item: Item;
}

export function ItemInfo({ item }: ItemInfoProps) {
  // Handle both field names: backend returns 'type', frontend uses 'item_type'
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
  
  // Format date for display
  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleDateString('zh-CN', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  return (
    <div className="space-y-4">
      {/* 标题和状态 */}
      <div>
        <h1 className="text-2xl font-semibold">{item.name}</h1>
        <div className="flex items-center gap-2 mt-2">
          <ItemTypeBadge itemType={itemType} />
          <StatusBadge status={displayStatus} type="item" />
          {!item.is_active && (
            <Badge variant="destructive">已停用</Badge>
          )}
        </div>
      </div>
      
      <Separator />
      
      {/* 基本信息 */}
      <div className="grid grid-cols-2 gap-4 text-sm">
        <InfoRow label="SKU" value={item.sku} mono />
        <InfoRow label="条码" value={item.barcode || '-'} mono />
        <InfoRow label="单位" value={item.unit || '-'} />
        <InfoRow 
          label="分类" 
          value={item.category_name || '-'} 
          icon={<FolderTree className="h-3.5 w-3.5" />}
        />
        <InfoRow 
          label="库位" 
          value={item.location_full_path || item.location_name || '-'} 
          icon={<MapPin className="h-3.5 w-3.5" />}
          className="col-span-2"
        />
        <InfoRow 
          label="仓库" 
          value={item.warehouse_code || '-'} 
        />
        <InfoRow 
          label="负责人" 
          value={item.owner_username || '-'} 
          icon={<User className="h-3.5 w-3.5" />}
        />
      </div>
      
      <Separator />
      
      {/* 类型特定信息 */}
      {itemType === 'consumable' && (
        <div className="grid grid-cols-2 gap-4 text-sm">
          <InfoRow 
            label="当前库存" 
            value={String(item.quantity ?? 0)} 
            icon={<Package className="h-3.5 w-3.5" />}
            highlight={item.status === 'out_of_stock'}
          />
          <InfoRow 
            label="低库存阈值" 
            value={String(item.low_stock_threshold ?? 0)} 
          />
        </div>
      )}
      
      {/* 可重复使用物品的数量信息 */}
      {itemType === 'reusable' && (
        <div className="grid grid-cols-2 gap-4 text-sm">
          <InfoRow 
            label="总数量" 
            value={String(item.quantity ?? 1)} 
            icon={<Package className="h-3.5 w-3.5" />}
          />
          <InfoRow 
            label="可借数量" 
            value={`${item.available_quantity ?? item.quantity ?? 1} / ${item.quantity ?? 1}`}
            highlight={(item.available_quantity ?? item.quantity ?? 1) === 0}
          />
        </div>
      )}
      
      {/* 借出状态显示当前借用人 - Requirements 5.3 */}
      {itemType === 'reusable' && item.status === 'borrowed' && (
        <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
          <div className="flex items-center gap-2 text-yellow-800">
            <User className="h-4 w-4" />
            <span className="font-medium">当前借用人</span>
          </div>
          <p className="mt-1 text-yellow-900 font-semibold">
            {item.current_borrower || '未知'}
          </p>
          {(item.borrowed_quantity ?? 0) > 0 && (item.quantity ?? 1) > 1 && (
            <p className="mt-1 text-sm text-yellow-700">
              已借出 {item.borrowed_quantity} 件
            </p>
          )}
        </div>
      )}
      
      {/* 描述 */}
      {item.description && (
        <>
          <Separator />
          <div>
            <h3 className="text-sm font-medium mb-2">描述</h3>
            <p className="text-sm text-muted-foreground whitespace-pre-wrap">
              {item.description}
            </p>
          </div>
        </>
      )}
      
      <Separator />
      
      {/* 时间信息 */}
      <div className="grid grid-cols-2 gap-4 text-sm">
        <InfoRow 
          label="创建时间" 
          value={formatDate(item.created_at)} 
          icon={<Calendar className="h-3.5 w-3.5" />}
        />
        <InfoRow 
          label="更新时间" 
          value={formatDate(item.updated_at)} 
          icon={<Calendar className="h-3.5 w-3.5" />}
        />
      </div>
    </div>
  );
}

interface InfoRowProps {
  label: string;
  value: string;
  mono?: boolean;
  className?: string;
  icon?: React.ReactNode;
  highlight?: boolean;
}

function InfoRow({ label, value, mono, className, icon, highlight }: InfoRowProps) {
  return (
    <div className={className}>
      <dt className="text-muted-foreground flex items-center gap-1.5">
        {icon}
        {label}
      </dt>
      <dd className={`${mono ? 'font-mono' : ''} ${highlight ? 'text-red-600 font-semibold' : ''}`}>
        {value}
      </dd>
    </div>
  );
}
