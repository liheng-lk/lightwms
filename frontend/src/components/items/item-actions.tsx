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
import { useAuth } from '@/providers/auth-provider';
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
  const { user } = useAuth();
  
  const ownerId = item.owner_id ?? (typeof item.owner === 'number' ? item.owner : undefined);
  const resource = { owner_id: ownerId };
  const canOperateItem = canOperate(resource);
  const canEditItem = canEdit(resource);
  const canDeleteItem = canDelete(resource);
  
  const itemType = item.item_type ?? item.type;
  const isReusable = itemType === 'reusable';
  const isConsumable = itemType === 'consumable';

  // Quantity-aware borrow state. Item.status alone cannot represent partial
  // borrowing: quantity 3 with one unit borrowed correctly remains available.
  const activeBorrows = (((item as any).active_borrows || []) as Array<{
    id: number;
    borrower: number;
    quantity: number;
  }>);
  const borrowedQuantity = item.borrowed_quantity ?? activeBorrows.reduce((sum, row) => sum + (row.quantity || 0), 0);
  const availableQuantity = item.available_quantity ?? Math.max((item.quantity ?? 0) - borrowedQuantity, 0);
  const hasActiveBorrow = activeBorrows.length > 0 || borrowedQuantity > 0 || item.status === 'borrowed';
  const hasOwnActiveBorrow = !!user?.id && activeBorrows.some((row) => row.borrower === user.id);
  const canReturnItem = isSuperAdmin || isItemManager || hasOwnActiveBorrow;
  
  const handlePrint = () => {
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
      {isReusable && (
        <>
          {availableQuantity > 0 && canOperateItem && onBorrow && (
            <Button onClick={onBorrow}>
              <ArrowLeftRight className="h-4 w-4 mr-2" />
              借出{(item.quantity ?? 1) > 1 ? `（可借 ${availableQuantity}）` : ''}
            </Button>
          )}
          {hasActiveBorrow && canReturnItem && onReturn && (
            <Button onClick={onReturn} variant={availableQuantity > 0 ? 'outline' : 'default'}>
              <ArrowLeftRight className="h-4 w-4 mr-2" />
              归还{borrowedQuantity > 0 ? `（已借 ${borrowedQuantity}）` : ''}
            </Button>
          )}
        </>
      )}
      
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
      
      {canEditItem && onEdit && (
        <Button variant="outline" onClick={onEdit}>
          <Edit className="h-4 w-4 mr-2" />
          编辑
        </Button>
      )}
      
      {canEditItem && onGenerateBarcode && !item.barcode && (
        <Button variant="outline" onClick={onGenerateBarcode}>
          <Barcode className="h-4 w-4 mr-2" />
          生成条码
        </Button>
      )}
      
      <Button variant="outline" onClick={handlePrint}>
        <Printer className="h-4 w-4 mr-2" />
        打印条码
      </Button>
      
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
                确定要停用物品「{item.name}」吗？停用前系统会检查是否还有未归还借用。
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
