'use client';

import { Button } from '@/components/ui/button';
import { 
  ArrowLeftRight, 
  Package, 
  PackagePlus, 
  Printer,
  Barcode,
  Edit,
  Ban,
} from 'lucide-react';
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
import { usePermissions } from '@/lib/hooks/use-permissions';
import type { Item } from '@/lib/types';

interface ItemActionsProps {
  item: Item;
  onBorrow?: () => void;
  onReturn?: () => void;
  onTake?: () => void;
  onReplenish?: () => void;
  onEdit?: () => void;
  onGenerateBarcode?: () => void;
  onDeactivate?: () => void;
}

export function ItemActions({
  item,
  onBorrow,
  onReturn,
  onTake,
  onReplenish,
  onEdit,
  onGenerateBarcode,
  onDeactivate,
}: ItemActionsProps) {
  const { canOperate, canEdit, canDelete, isSuperAdmin, isItemManager } = usePermissions();
  
  // Create resource object for permission check
  // Backend returns 'owner' as user ID (number), frontend type also has optional 'owner_id'
  const ownerId = item.owner_id ?? (typeof item.owner === 'number' ? item.owner : undefined);
  const resource = { owner_id: ownerId };
  
  // Check if user can operate on this item
  // item_manager can operate on all items (borrow, take, replenish)
  const canOperateItem = canOperate(resource);
  const canEditItem = canEdit(resource);
  const canDeleteItem = canDelete(resource);
  
  // For return operation:
  // - super_admin can return any item
  // - item_manager can return items they lent out (backend will verify)
  // We show the button for item_manager, backend will do the final check
  const canReturnItem = isSuperAdmin || isItemManager;
  
  // Determine item type - backend returns 'type', frontend uses 'item_type'
  // Handle both field names for compatibility
  const itemType = item.item_type ?? item.type;
  const isReusable = itemType === 'reusable';
  const isConsumable = itemType === 'consumable';
  
  const handlePrint = () => {
    // Simple barcode print functionality
    const printWindow = window.open('', '_blank');
    if (printWindow) {
      printWindow.document.write(`
        <html>
          <head>
            <title>打印条码 - ${item.sku}</title>
            <style>
              body { font-family: monospace; text-align: center; padding: 20px; }
              .sku { font-size: 24px; font-weight: bold; }
              .barcode { font-size: 18px; margin-top: 10px; }
              .name { font-size: 14px; margin-top: 10px; color: #666; }
            </style>
          </head>
          <body>
            <div class="sku">${item.sku}</div>
            ${item.barcode ? `<div class="barcode">${item.barcode}</div>` : ''}
            <div class="name">${item.name}</div>
          </body>
        </html>
      `);
      printWindow.document.close();
      printWindow.print();
    }
  };
  
  return (
    <div className="flex flex-wrap gap-2">
      {/* Reusable item operations - Requirements 5.5 */}
      {isReusable && (
        <>
          {item.status === 'available' && canOperateItem && onBorrow && (
            <Button onClick={onBorrow}>
              <ArrowLeftRight className="h-4 w-4 mr-2" />
              借出
            </Button>
          )}
          {item.status === 'borrowed' && canReturnItem && onReturn && (
            <Button onClick={onReturn}>
              <ArrowLeftRight className="h-4 w-4 mr-2" />
              归还
            </Button>
          )}
        </>
      )}
      
      {/* Consumable item operations - Requirements 5.5 */}
      {isConsumable && (
        <>
          {(item.quantity ?? 0) > 0 && canOperateItem && onTake && (
            <Button onClick={onTake}>
              <Package className="h-4 w-4 mr-2" />
              领用
            </Button>
          )}
          {canOperateItem && onReplenish && (
            <Button variant="outline" onClick={onReplenish}>
              <PackagePlus className="h-4 w-4 mr-2" />
              补货
            </Button>
          )}
        </>
      )}
      
      {/* Edit button */}
      {canEditItem && onEdit && (
        <Button variant="outline" onClick={onEdit}>
          <Edit className="h-4 w-4 mr-2" />
          编辑
        </Button>
      )}
      
      {/* Generate barcode button */}
      {canEditItem && onGenerateBarcode && !item.barcode && (
        <Button variant="outline" onClick={onGenerateBarcode}>
          <Barcode className="h-4 w-4 mr-2" />
          生成条码
        </Button>
      )}
      
      {/* Print barcode button */}
      <Button variant="outline" onClick={handlePrint}>
        <Printer className="h-4 w-4 mr-2" />
        打印条码
      </Button>
      
      {/* Deactivate button */}
      {canDeleteItem && item.is_active && onDeactivate && (
        <AlertDialog>
          <AlertDialogTrigger asChild>
            <Button variant="outline" className="text-destructive hover:text-destructive">
              <Ban className="h-4 w-4 mr-2" />
              停用
            </Button>
          </AlertDialogTrigger>
          <AlertDialogContent>
            <AlertDialogHeader>
              <AlertDialogTitle>确认停用物品</AlertDialogTitle>
              <AlertDialogDescription>
                确定要停用物品「{item.name}」吗？停用后该物品将不再显示在列表中。
              </AlertDialogDescription>
            </AlertDialogHeader>
            <AlertDialogFooter>
              <AlertDialogCancel>取消</AlertDialogCancel>
              <AlertDialogAction onClick={onDeactivate}>
                确认停用
              </AlertDialogAction>
            </AlertDialogFooter>
          </AlertDialogContent>
        </AlertDialog>
      )}
    </div>
  );
}
