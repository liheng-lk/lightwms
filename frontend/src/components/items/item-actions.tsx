'use client';

import { Button } from '@/components/ui/button';
import { 
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
import { escapeHtml } from '@/lib/html';

interface ItemActionsProps {
  item: Item;
  onEdit?: () => void;
  onGenerateBarcode?: () => void;
  onDeactivate?: () => void;
}

export function ItemActions({
  item,
  onEdit,
  onGenerateBarcode,
  onDeactivate,
}: ItemActionsProps) {
  const { canEdit, canDelete } = usePermissions();
  
  const ownerId = item.owner_id ?? (typeof item.owner === 'number' ? item.owner : undefined);
  const resource = { owner_id: ownerId };
  const canEditItem = canEdit(resource);
  const canDeleteItem = canDelete(resource);
  
  const handlePrint = () => {
    const printWindow = window.open('', '_blank');
    if (printWindow) {
      printWindow.document.write(`
        <html>
          <head>
            <title>打印条码 - ${escapeHtml(item.sku)}</title>
            <style>
              body { font-family: monospace; text-align: center; padding: 20px; }
              .sku { font-size: 24px; font-weight: bold; }
              .barcode { font-size: 18px; margin-top: 10px; }
              .name { font-size: 14px; margin-top: 10px; color: #666; }
            </style>
          </head>
          <body>
            <div class="sku">${escapeHtml(item.sku)}</div>
            ${item.barcode ? `<div class="barcode">${escapeHtml(item.barcode)}</div>` : ''}
            <div class="name">${escapeHtml(item.name)}</div>
          </body>
        </html>
      `);
      printWindow.document.close();
      printWindow.print();
    }
  };
  
  return (
    <div className="flex flex-wrap gap-2">
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
                确定要停用物品「{item.name}」吗？停用后不再出现在日常列表，需要时可再查看历史。
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
