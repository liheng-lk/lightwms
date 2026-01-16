'use client';

import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
  DialogDescription,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Label } from '@/components/ui/label';
import { InvoiceStatusBadge } from './invoice-status-badge';
import { useUpdateInvoiceStatus } from '@/lib/hooks/use-invoices';
import { useState, useEffect } from 'react';
import type { Invoice, InvoiceStatus } from '@/lib/types';

interface InvoiceStatusDialogProps {
  invoice?: Invoice;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSuccess?: () => void;
}

export function InvoiceStatusDialog({
  invoice,
  open,
  onOpenChange,
  onSuccess,
}: InvoiceStatusDialogProps) {
  const { mutate: updateStatus, isPending } = useUpdateInvoiceStatus();
  const [selectedStatus, setSelectedStatus] = useState<InvoiceStatus>('pending');

  // Reset selected status when dialog opens
  useEffect(() => {
    if (open && invoice) {
      setSelectedStatus(invoice.status);
    }
  }, [open, invoice]);

  const handleSubmit = () => {
    if (!invoice) return;

    updateStatus(
      { id: invoice.id, status: selectedStatus },
      {
        onSuccess: () => {
          onOpenChange(false);
          onSuccess?.();
        },
      }
    );
  };

  if (!invoice) return null;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[400px]">
        <DialogHeader>
          <DialogTitle>修改报销状态</DialogTitle>
          <DialogDescription>
            修改发票 "{invoice.name}" 的报销状态
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-4">
          {/* 当前状态 */}
          <div className="flex items-center justify-between">
            <Label>当前状态</Label>
            <InvoiceStatusBadge status={invoice.status} />
          </div>

          {/* 新状态选择 */}
          <div className="space-y-2">
            <Label>新状态</Label>
            <Select
              value={selectedStatus}
              onValueChange={(v) => setSelectedStatus(v as InvoiceStatus)}
            >
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="pending">
                  <div className="flex items-center gap-2">
                    <span className="w-2 h-2 rounded-full bg-yellow-500" />
                    未报销
                  </div>
                </SelectItem>
                <SelectItem value="reimbursed">
                  <div className="flex items-center gap-2">
                    <span className="w-2 h-2 rounded-full bg-green-500" />
                    已报销
                  </div>
                </SelectItem>
                <SelectItem value="rejected">
                  <div className="flex items-center gap-2">
                    <span className="w-2 h-2 rounded-full bg-red-500" />
                    无法报销
                  </div>
                </SelectItem>
              </SelectContent>
            </Select>
          </div>

          {/* 发票信息摘要 */}
          <div className="text-sm text-muted-foreground space-y-1 pt-2 border-t">
            <div className="flex justify-between">
              <span>金额</span>
              <span className="font-mono">
                {new Intl.NumberFormat('zh-CN', {
                  style: 'currency',
                  currency: 'CNY',
                }).format(invoice.amount)}
              </span>
            </div>
            <div className="flex justify-between">
              <span>类别</span>
              <span>{invoice.category}</span>
            </div>
            <div className="flex justify-between">
              <span>登记月份</span>
              <span>{invoice.registered_month}</span>
            </div>
          </div>
        </div>

        <DialogFooter>
          <Button
            type="button"
            variant="outline"
            onClick={() => onOpenChange(false)}
          >
            取消
          </Button>
          <Button
            onClick={handleSubmit}
            disabled={isPending || selectedStatus === invoice.status}
          >
            {isPending ? '更新中...' : '确认修改'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
