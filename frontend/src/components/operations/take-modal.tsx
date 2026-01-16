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
import { useTake } from '@/lib/hooks/use-operations';
import type { Item } from '@/lib/types';

interface TakeModalProps {
  item: Item;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSuccess?: () => void;
}

export function TakeModal({ item, open, onOpenChange, onSuccess }: TakeModalProps) {
  const takeSchema = z.object({
    taker: z.number({ error: '请选择领用人' }),
    quantity: z
      .number({ error: '请输入数量' })
      .min(1, '数量至少为 1')
      .max(item.quantity ?? 0, `数量不能超过当前库存 ${item.quantity ?? 0}`),
    note: z.string().optional(),
  });
  
  type TakeForm = z.infer<typeof takeSchema>;
  
  const { mutate, isPending } = useTake();
  
  const {
    register,
    handleSubmit,
    setValue,
    watch,
    reset,
    formState: { errors },
  } = useForm<TakeForm>({
    resolver: zodResolver(takeSchema),
    defaultValues: {
      quantity: 1,
    },
  });
  
  const taker = watch('taker');
  
  const onSubmit = (data: TakeForm) => {
    mutate(
      {
        itemId: item.id,
        taker: data.taker,
        quantity: data.quantity,
        notes: data.note || undefined,
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
  
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>领用物品</DialogTitle>
        </DialogHeader>
        
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          <div className="text-sm text-muted-foreground">
            物品：{item.name} ({item.sku})
          </div>
          <div className="text-sm">
            当前库存：<span className="font-medium">{item.quantity ?? 0}</span>
          </div>
          
          <div className="space-y-2">
            <Label>领用人 *</Label>
            <UserSelect
              value={taker}
              onChange={(v) => setValue('taker', v as number)}
              placeholder="选择领用人"
            />
            {errors.taker && (
              <p className="text-sm text-destructive">{errors.taker.message}</p>
            )}
          </div>
          
          <div className="space-y-2">
            <Label htmlFor="quantity">领用数量 *</Label>
            <Input
              id="quantity"
              type="number"
              min={1}
              max={item.quantity ?? 0}
              placeholder="例如：10"
              {...register('quantity', { valueAsNumber: true })}
            />
            {errors.quantity && (
              <p className="text-sm text-destructive">{errors.quantity.message}</p>
            )}
          </div>
          
          <div className="space-y-2">
            <Label htmlFor="note">用途备注</Label>
            <Textarea
              id="note"
              placeholder="例如：部门会议使用 / 客户拜访礼品"
              {...register('note')}
            />
          </div>
          
          <div className="flex justify-end gap-2">
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
              取消
            </Button>
            <Button type="submit" disabled={isPending}>
              {isPending ? '处理中...' : '确认领用'}
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  );
}
