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
import { useReplenish } from '@/lib/hooks/use-operations';
import type { Item } from '@/lib/types';

const replenishSchema = z.object({
  quantity: z
    .number({ error: '请输入数量' })
    .min(1, '数量至少为 1'),
  note: z.string().optional(),
});

type ReplenishForm = z.infer<typeof replenishSchema>;

interface ReplenishModalProps {
  item: Item;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSuccess?: () => void;
}

export function ReplenishModal({ item, open, onOpenChange, onSuccess }: ReplenishModalProps) {
  const { mutate, isPending } = useReplenish();
  
  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<ReplenishForm>({
    resolver: zodResolver(replenishSchema),
    defaultValues: {
      quantity: 1,
    },
  });
  
  const onSubmit = (data: ReplenishForm) => {
    mutate(
      {
        itemId: item.id,
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
          <DialogTitle>补货</DialogTitle>
        </DialogHeader>
        
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          <div className="text-sm text-muted-foreground">
            物品：{item.name} ({item.sku})
          </div>
          <div className="text-sm">
            当前库存：<span className="font-medium">{item.quantity ?? 0}</span>
          </div>
          
          <div className="space-y-2">
            <Label htmlFor="quantity">补货数量 *</Label>
            <Input
              id="quantity"
              type="number"
              min={1}
              placeholder="例如：50"
              {...register('quantity', { valueAsNumber: true })}
            />
            {errors.quantity && (
              <p className="text-sm text-destructive">{errors.quantity.message}</p>
            )}
          </div>
          
          <div className="space-y-2">
            <Label htmlFor="note">来源备注</Label>
            <Textarea
              id="note"
              placeholder="例如：采购入库 / 其他仓库调拨 / 供应商补货"
              {...register('note')}
            />
          </div>
          
          <div className="flex justify-end gap-2">
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
              取消
            </Button>
            <Button type="submit" disabled={isPending}>
              {isPending ? '处理中...' : '确认补货'}
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  );
}
