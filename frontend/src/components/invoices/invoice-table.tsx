'use client';

import { useState } from 'react';
import { FileText, ExternalLink, MoreHorizontal, Pencil, Trash2 } from 'lucide-react';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import { Checkbox } from '@/components/ui/checkbox';
import { InvoiceStatusBadge } from './invoice-status-badge';
import { useDeleteInvoice } from '@/lib/hooks/use-invoices';
import { usePermissions } from '@/lib/hooks/use-permissions';
import { formatDate } from '@/lib/utils/date';
import type { Invoice } from '@/lib/types';

interface InvoiceTableProps {
  invoices: Invoice[];
  isLoading?: boolean;
  onEdit?: (invoice: Invoice) => void;
  onStatusChange?: (invoice: Invoice) => void;
  selectable?: boolean;
  selectedIds?: number[];
  onSelectionChange?: (ids: number[]) => void;
}

export function InvoiceTable({
  invoices,
  isLoading,
  onEdit,
  onStatusChange,
  selectable = false,
  selectedIds = [],
  onSelectionChange,
}: InvoiceTableProps) {
  const { canDelete } = usePermissions();
  const { mutate: deleteInvoice, isPending: isDeleting } = useDeleteInvoice();
  const [deleteId, setDeleteId] = useState<number | null>(null);

  const handleDelete = () => {
    if (deleteId) {
      deleteInvoice(deleteId, {
        onSuccess: () => setDeleteId(null),
      });
    }
  };

  const formatAmount = (amount: number) => {
    return new Intl.NumberFormat('zh-CN', {
      style: 'currency',
      currency: 'CNY',
    }).format(amount);
  };

  // Individual invoice deletion is an inventory-management action; status
  // approval is only rendered when the parent supplies the Super Admin handler.
  const userCanDelete = canDelete();
  const canChangeStatus = !!onStatusChange;

  const handleSelectAll = (checked: boolean) => {
    if (!onSelectionChange) return;
    if (checked) {
      onSelectionChange(invoices.map(inv => inv.id));
    } else {
      onSelectionChange([]);
    }
  };

  const handleSelectItem = (invoiceId: number, checked: boolean) => {
    if (!onSelectionChange) return;
    if (checked) {
      onSelectionChange([...selectedIds, invoiceId]);
    } else {
      onSelectionChange(selectedIds.filter(id => id !== invoiceId));
    }
  };

  const allSelected = invoices.length > 0 && invoices.every(inv => selectedIds.includes(inv.id));
  const someSelected = selectedIds.length > 0 && !allSelected;

  if (isLoading) {
    return <InvoiceTableSkeleton showCheckbox={selectable} />;
  }

  if (invoices.length === 0) {
    return (
      <div className="text-center py-12 text-muted-foreground">
        暂无发票数据
      </div>
    );
  }

  return (
    <>
      <div className="rounded-md border">
        <Table>
          <TableHeader>
            <TableRow>
              {selectable && (
                <TableHead className="w-[40px]">
                  <Checkbox
                    checked={allSelected}
                    onCheckedChange={handleSelectAll}
                    aria-label="全选"
                    {...(someSelected ? { 'data-state': 'indeterminate' } : {})}
                  />
                </TableHead>
              )}
              <TableHead>发票名称</TableHead>
              <TableHead>金额</TableHead>
              <TableHead>类别</TableHead>
              <TableHead>项目</TableHead>
              <TableHead>状态</TableHead>
              <TableHead>关联物品</TableHead>
              <TableHead>上传人</TableHead>
              <TableHead>登记月份</TableHead>
              <TableHead className="w-[80px]">操作</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {invoices.map((invoice) => {
              const isSelected = selectedIds.includes(invoice.id);

              return (
                <TableRow key={invoice.id} data-state={isSelected ? 'selected' : undefined}>
                  {selectable && (
                    <TableCell>
                      <Checkbox
                        checked={isSelected}
                        onCheckedChange={(checked) => handleSelectItem(invoice.id, !!checked)}
                        aria-label={`选择 ${invoice.name}`}
                      />
                    </TableCell>
                  )}
                  <TableCell>
                    <div className="flex items-center gap-2">
                      <FileText className="h-4 w-4 text-muted-foreground" />
                      <span className="font-medium">{invoice.name}</span>
                    </div>
                  </TableCell>
                  <TableCell className="font-mono">
                    {formatAmount(invoice.amount)}
                  </TableCell>
                  <TableCell>
                    <span className="text-sm">{invoice.category}</span>
                    {invoice.custom_type && (
                      <span className="text-xs text-muted-foreground ml-1">
                        ({invoice.custom_type})
                      </span>
                    )}
                  </TableCell>
                  <TableCell>
                    {invoice.project ? (
                      <span className="text-sm">{invoice.project}</span>
                    ) : (
                      <span className="text-muted-foreground text-sm">-</span>
                    )}
                  </TableCell>
                  <TableCell>
                    {canChangeStatus ? (
                      <button
                        onClick={() => onStatusChange?.(invoice)}
                        className="cursor-pointer"
                      >
                        <InvoiceStatusBadge status={invoice.status} />
                      </button>
                    ) : (
                      <InvoiceStatusBadge status={invoice.status} />
                    )}
                  </TableCell>
                  <TableCell>
                    {invoice.item_name ? (
                      <span className="text-sm">{invoice.item_name}</span>
                    ) : (
                      <span className="text-muted-foreground text-sm">-</span>
                    )}
                  </TableCell>
                  <TableCell>
                    <span className="text-sm">{invoice.created_by_username}</span>
                  </TableCell>
                  <TableCell>{invoice.registered_month}</TableCell>
                  <TableCell>
                    <DropdownMenu>
                      <DropdownMenuTrigger asChild>
                        <Button variant="ghost" size="icon" className="h-8 w-8">
                          <MoreHorizontal className="h-4 w-4" />
                        </Button>
                      </DropdownMenuTrigger>
                      <DropdownMenuContent align="end">
                        {invoice.file && (
                          <DropdownMenuItem asChild>
                            <a
                              href={`/api/media/${invoice.file.replace(/^\/?media\//, '')}`}
                              target="_blank"
                              rel="noopener noreferrer"
                            >
                              <ExternalLink className="h-4 w-4 mr-2" />
                              查看文件
                            </a>
                          </DropdownMenuItem>
                        )}
                        {onEdit && (
                          <DropdownMenuItem onClick={() => onEdit(invoice)}>
                            <Pencil className="h-4 w-4 mr-2" />
                            编辑
                          </DropdownMenuItem>
                        )}
                        {userCanDelete && (
                          <DropdownMenuItem
                            onClick={() => setDeleteId(invoice.id)}
                            className="text-destructive"
                          >
                            <Trash2 className="h-4 w-4 mr-2" />
                            删除
                          </DropdownMenuItem>
                        )}
                      </DropdownMenuContent>
                    </DropdownMenu>
                  </TableCell>
                </TableRow>
              );
            })}
          </TableBody>
        </Table>
      </div>

      <AlertDialog open={!!deleteId} onOpenChange={(open) => !open && setDeleteId(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>确认删除</AlertDialogTitle>
            <AlertDialogDescription>
              确定要删除这张发票吗？此操作无法撤销。
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel disabled={isDeleting}>取消</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleDelete}
              disabled={isDeleting}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              {isDeleting ? '删除中...' : '确认删除'}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </>
  );
}

interface InvoiceTableSkeletonProps {
  showCheckbox?: boolean;
}

function InvoiceTableSkeleton({ showCheckbox }: InvoiceTableSkeletonProps) {
  return (
    <div className="rounded-md border">
      <Table>
        <TableHeader>
          <TableRow>
            {showCheckbox && (
              <TableHead className="w-[40px]">
                <Skeleton className="h-4 w-4" />
              </TableHead>
            )}
            <TableHead>发票名称</TableHead>
            <TableHead>金额</TableHead>
            <TableHead>类别</TableHead>
            <TableHead>项目</TableHead>
            <TableHead>状态</TableHead>
            <TableHead>关联物品</TableHead>
            <TableHead>上传人</TableHead>
            <TableHead>登记月份</TableHead>
            <TableHead className="w-[80px]">操作</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {Array.from({ length: 5 }).map((_, i) => (
            <TableRow key={i}>
              {showCheckbox && (
                <TableCell><Skeleton className="h-4 w-4" /></TableCell>
              )}
              <TableCell><Skeleton className="h-4 w-32" /></TableCell>
              <TableCell><Skeleton className="h-4 w-20" /></TableCell>
              <TableCell><Skeleton className="h-4 w-16" /></TableCell>
              <TableCell><Skeleton className="h-4 w-16" /></TableCell>
              <TableCell><Skeleton className="h-5 w-14" /></TableCell>
              <TableCell><Skeleton className="h-4 w-16" /></TableCell>
              <TableCell><Skeleton className="h-4 w-16" /></TableCell>
              <TableCell><Skeleton className="h-4 w-20" /></TableCell>
              <TableCell><Skeleton className="h-8 w-8" /></TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}
