'use client';

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
import { useReturn } from '@/lib/hooks/use-operations';
import { useAuth } from '@/providers/auth-provider';
import type { Item } from '@/lib/types';

const returnSchema = z.object({
  return_notes: z.string().optional(),
  condition: z.string().optional(),
});

type ReturnForm = z.infer<typeof returnSchema>;

interface ReturnModalProps {
  item: Item;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSuccess?: () => void;
}

export function ReturnModal({ item, open, onOpenChange, onSuccess }: ReturnModalProps) {
  const { mutate, isPending } = useReturn();
  const { user } = useAuth();
  
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
  
  // Check if current user is the borrower (not owner/admin)
  // Borrowers cannot set the condition field
  const isBorrower = user && item.current_borrow_record_id && 
    user.role !== 'super_admin' && 
    item.owner !== user.id && 
    item.owner_id !== user.id;
  
  const onSubmit = (data: ReturnForm) => {
    mutate(
      {
        itemId: item.id,
        params: {
          return_notes: data.return_notes || undefined,
          // Only include condition if user is not the borrower
          condition: isBorrower ? undefined : (data.condition || undefined),
        },
      },
      {
        onSuccess: () => {
          reset();
          onOpenChange(false);
          onSuccess?.();
        },
      }
    );
  };

  const handleOpenChange = (newOpen: boolean) => {
    if (!newOpen) {
      reset();
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
          
          {item.current_borrower && (
            <div className="text-sm">
              当前借用人：<span className="font-medium">{item.current_borrower}</span>
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
          
          {/* Only show condition field for owner/admin, not for borrower */}
          {!isBorrower && (
            <div className="space-y-2">
              <Label htmlFor="condition">物品状况</Label>
              <Textarea
                id="condition"
                placeholder="例如：完好无损 / 轻微磨损 / 需要维修"
                {...register('condition')}
              />
              <p className="text-xs text-muted-foreground">
                记录物品归还时的状况，便于追踪物品使用情况
              </p>
            </div>
          )}
          
          <div className="flex justify-end gap-2">
            <Button type="button" variant="outline" onClick={() => handleOpenChange(false)}>
              取消
            </Button>
            <Button type="submit" disabled={isPending}>
              {isPending ? '处理中...' : '确认归还'}
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  );
}
