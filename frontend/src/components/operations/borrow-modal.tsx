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
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { UserSelect } from './user-select';
import { useBorrow } from '@/lib/hooks/use-operations';
import type { Item } from '@/lib/types';

// Get today's date in YYYY-MM-DD format for min date validation
const getTodayString = () => {
  const today = new Date();
  return today.toISOString().split('T')[0];
};

const borrowSchema = z.object({
  borrower: z.number({ error: '请选择借用人' }),
  quantity: z.number().min(1, '数量至少为1'),
  expected_return_date: z.string({ error: '请选择预计归还日期' })
    .min(1, '请选择预计归还日期')
    .refine((date) => {
      const selected = new Date(date);
      const today = new Date();
      today.setHours(0, 0, 0, 0);
      return selected >= today;
    }, '预计归还日期不能早于今天'),
  notes: z.string().optional(),
});

type BorrowForm = z.infer<typeof borrowSchema>;

interface BorrowModalProps {
  item: Item;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSuccess?: () => void;
}

export function BorrowModal({ item, open, onOpenChange, onSuccess }: BorrowModalProps) {
  const { mutate, isPending } = useBorrow();
  
  // Calculate available quantity
  const availableQuantity = item.available_quantity ?? (item.quantity ?? 1);
  const totalQuantity = item.quantity ?? 1;
  const showQuantityInput = totalQuantity > 1;
  
  const {
    register,
    handleSubmit,
    setValue,
    watch,
    reset,
    formState: { errors },
  } = useForm<BorrowForm>({
    resolver: zodResolver(borrowSchema),
    defaultValues: {
      quantity: 1,
      notes: '',
    },
  });
  
  const borrower = watch('borrower');
  const quantity = watch('quantity');
  
  const onSubmit = (data: BorrowForm) => {
    mutate(
      {
        itemId: item.id,
        borrower: data.borrower,
        quantity: data.quantity,
        expected_return_date: data.expected_return_date,
        notes: data.notes || undefined,
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
          <DialogTitle>借出物品</DialogTitle>
        </DialogHeader>
        
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          <div className="text-sm text-muted-foreground">
            物品：{item.name} ({item.sku})
            {showQuantityInput && (
              <span className="ml-2">
                · 可借数量：<span className="font-medium text-foreground">{availableQuantity}</span> / {totalQuantity}
              </span>
            )}
          </div>
          
          <div className="space-y-2">
            <Label>借用人 *</Label>
            <UserSelect
              value={borrower}
              onChange={(v) => setValue('borrower', v as number)}
              placeholder="选择借用人"
            />
            {errors.borrower && (
              <p className="text-sm text-destructive">{errors.borrower.message}</p>
            )}
          </div>
          
          {showQuantityInput && (
            <div className="space-y-2">
              <Label htmlFor="quantity">借用数量 *</Label>
              <Input
                id="quantity"
                type="number"
                min={1}
                max={availableQuantity}
                {...register('quantity', { valueAsNumber: true })}
              />
              {errors.quantity && (
                <p className="text-sm text-destructive">{errors.quantity.message}</p>
              )}
              {quantity > availableQuantity && (
                <p className="text-sm text-destructive">借用数量不能超过可用数量 ({availableQuantity})</p>
              )}
            </div>
          )}
          
          <div className="space-y-2">
            <Label htmlFor="expected_return_date">预计归还日期 *</Label>
            <Input
              id="expected_return_date"
              type="date"
              min={getTodayString()}
              {...register('expected_return_date')}
            />
            {errors.expected_return_date && (
              <p className="text-sm text-destructive">{errors.expected_return_date.message}</p>
            )}
          </div>
          
          <div className="space-y-2">
            <Label htmlFor="notes">备注</Label>
            <Textarea
              id="notes"
              placeholder="例如：用于项目演示，预计使用一周"
              {...register('notes')}
            />
          </div>
          
          <div className="flex justify-end gap-2">
            <Button type="button" variant="outline" onClick={() => handleOpenChange(false)}>
              取消
            </Button>
            <Button type="submit" disabled={isPending || (showQuantityInput && quantity > availableQuantity)}>
              {isPending ? '处理中...' : '确认借出'}
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  );
}
