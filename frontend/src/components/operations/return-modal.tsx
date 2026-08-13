'use client';

import { useEffect, useMemo, useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Label } from '@/components/ui/label';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { useReturn } from '@/lib/hooks/use-operations';
import { useAuth } from '@/providers/auth-provider';
import type { Item } from '@/lib/types';

const returnSchema = z.object({
  return_notes: z.string().optional(),
  condition: z.string().optional(),
});

type ReturnForm = z.infer<typeof returnSchema>;

type ActiveBorrowSummary = {
  id: number;
  borrower: number;
  borrower_username: string;
  quantity: number;
  expected_return_date?: string;
  computed_status?: string;
};

interface ReturnModalProps {
  item: Item;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSuccess?: () => void;
}

export function ReturnModal({ item, open, onOpenChange, onSuccess }: ReturnModalProps) {
  const { mutate, isPending } = useReturn();
  const { user } = useAuth();
  const [selectedRecordId, setSelectedRecordId] = useState('');

  const activeBorrows = (((item as any).active_borrows || []) as ActiveBorrowSummary[]);
  const canManageReturns = user?.role === 'super_admin' || user?.role === 'item_manager';
  const isBorrower = !!user && !canManageReturns;

  const eligibleBorrows = useMemo(() => {
    if (canManageReturns) return activeBorrows;
    if (!user?.id) return [];
    return activeBorrows.filter((record) => record.borrower === user.id);
  }, [activeBorrows, canManageReturns, user?.id]);

  const {
    register,
    handleSubmit,
    reset,
  } = useForm<ReturnForm>({
    resolver: zodResolver(returnSchema),
    defaultValues: {
      return_notes: '',
      condition: '',
    },
  });

  useEffect(() => {
    if (!open) return;
    if (eligibleBorrows.length === 1) {
      setSelectedRecordId(String(eligibleBorrows[0].id));
    } else if (eligibleBorrows.length > 1) {
      setSelectedRecordId('');
    } else if ((item as any).current_borrow_record_id) {
      // Legacy single-record API fallback.
      setSelectedRecordId(String((item as any).current_borrow_record_id));
    } else {
      setSelectedRecordId('');
    }
  }, [open, item, eligibleBorrows]);

  const selectedBorrow = eligibleBorrows.find(
    (record) => String(record.id) === selectedRecordId
  );
  const requiresSelection = eligibleBorrows.length > 1;

  const onSubmit = (data: ReturnForm) => {
    if (requiresSelection && !selectedRecordId) return;

    mutate(
      {
        itemId: item.id,
        params: {
          ...(selectedRecordId ? { borrow_record_id: Number(selectedRecordId) } : {}),
          return_notes: data.return_notes || undefined,
          condition: isBorrower ? undefined : (data.condition || undefined),
        } as any,
      },
      {
        onSuccess: () => {
          reset();
          setSelectedRecordId('');
          onOpenChange(false);
          onSuccess?.();
        },
      }
    );
  };

  const handleOpenChange = (newOpen: boolean) => {
    if (!newOpen) {
      reset();
      setSelectedRecordId('');
    }
    onOpenChange(newOpen);
  };
  
  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>归还物品</DialogTitle>
        </DialogHeader>
        
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          <div className="text-sm text-muted-foreground">
            物品：{item.name} ({item.sku})
          </div>

          {eligibleBorrows.length > 1 && (
            <div className="space-y-2">
              <Label>选择要归还的借用记录</Label>
              <Select value={selectedRecordId} onValueChange={setSelectedRecordId}>
                <SelectTrigger>
                  <SelectValue placeholder="请选择借用人 / 借用批次" />
                </SelectTrigger>
                <SelectContent>
                  {eligibleBorrows.map((record) => (
                    <SelectItem key={record.id} value={String(record.id)}>
                      {record.borrower_username} · {record.quantity} 件
                      {record.expected_return_date ? ` · 应还 ${record.expected_return_date}` : ''}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <p className="text-xs text-muted-foreground">
                同一物品存在多条未归还记录，必须明确选择，系统不会再自动归还第一条记录。
              </p>
            </div>
          )}

          {eligibleBorrows.length === 1 && (
            <div className="rounded-md bg-muted/50 p-3 text-sm space-y-1">
              <div>
                借用人：<span className="font-medium">{eligibleBorrows[0].borrower_username}</span>
              </div>
              <div>本次归还数量：{eligibleBorrows[0].quantity} 件</div>
              {eligibleBorrows[0].expected_return_date && (
                <div>预计归还：{eligibleBorrows[0].expected_return_date}</div>
              )}
            </div>
          )}

          {selectedBorrow && eligibleBorrows.length > 1 && (
            <div className="text-sm text-muted-foreground">
              本次归还 {selectedBorrow.quantity} 件，借用人：{selectedBorrow.borrower_username}
            </div>
          )}

          {eligibleBorrows.length === 0 && (item as any).current_borrower && (
            <div className="text-sm">
              当前借用人：<span className="font-medium">{(item as any).current_borrower}</span>
            </div>
          )}
          
          <div className="space-y-2">
            <Label htmlFor="return_notes">归还备注</Label>
            <Textarea
              id="return_notes"
              placeholder="例如：已清洁消毒，功能正常"
              {...register('return_notes')}
            />
          </div>
          
          {!isBorrower && (
            <div className="space-y-2">
              <Label htmlFor="condition">物品状况</Label>
              <Textarea
                id="condition"
                placeholder="例如：完好无损 / 轻微磨损 / 需要维修"
                {...register('condition')}
              />
              <p className="text-xs text-muted-foreground">
                记录这一批次物品归还时的状况
              </p>
            </div>
          )}
          
          <div className="flex justify-end gap-2">
            <Button type="button" variant="outline" onClick={() => handleOpenChange(false)}>
              取消
            </Button>
            <Button type="submit" disabled={isPending || (requiresSelection && !selectedRecordId)}>
              {isPending ? '处理中...' : '确认归还'}
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  );
}
