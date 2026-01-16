'use client';

import { useState } from 'react';
import Link from 'next/link';
import { Trash2 } from 'lucide-react';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { Button } from '@/components/ui/button';
import { Checkbox } from '@/components/ui/checkbox';
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
import { Skeleton } from '@/components/ui/skeleton';
import { StatusBadge } from '@/components/ui/status-badge';
import { formatDateTime } from '@/lib/utils/date';
import { useDeleteBorrowRecord } from '@/lib/hooks/use-records';
import { usePermissions } from '@/lib/hooks/use-permissions';
import type { BorrowRecord } from '@/lib/types';

interface BorrowRecordTableProps {
  records: BorrowRecord[];
  isLoading?: boolean;
  selectedIds?: number[];
  onSelectionChange?: (ids: number[]) => void;
}

export function BorrowRecordTable({ records, isLoading, selectedIds = [], onSelectionChange }: BorrowRecordTableProps) {
  const [deleteId, setDeleteId] = useState<number | null>(null);
  const { mutate: deleteRecord, isPending: isDeleting } = useDeleteBorrowRecord();
  const { isSuperAdmin } = usePermissions();
  
  // 只要传入了 onSelectionChange 就显示复选框
  const showSelection = !!onSelectionChange;
  
  const handleSelectAll = (checked: boolean) => {
    if (!onSelectionChange) return;
    onSelectionChange(checked ? records.map(r => r.id) : []);
  };
  
  const handleSelectOne = (id: number, checked: boolean) => {
    if (!onSelectionChange) return;
    onSelectionChange(
      checked ? [...selectedIds, id] : selectedIds.filter(i => i !== id)
    );
  };
  
  const allSelected = records.length > 0 && selectedIds.length === records.length;
  const someSelected = selectedIds.length > 0 && selectedIds.length < records.length;
  
  const handleDelete = () => {
    if (deleteId) {
      deleteRecord(deleteId, {
        onSuccess: () => setDeleteId(null),
      });
    }
  };
  
  if (isLoading) {
    return <BorrowRecordTableSkeleton showSelection={!!showSelection} />;
  }
  
  if (records.length === 0) {
    return (
      <div className="text-center py-12 text-muted-foreground">
        暂无借出记录
      </div>
    );
  }
  
  return (
    <>
      <div className="border rounded-lg overflow-hidden">
        <Table>
          <TableHeader>
            <TableRow>
              {showSelection && (
                <TableHead className="w-[40px]">
                  <Checkbox
                    checked={allSelected}
                    ref={(el) => {
                      if (el) (el as HTMLButtonElement & { indeterminate: boolean }).indeterminate = someSelected;
                    }}
                    onCheckedChange={handleSelectAll}
                  />
                </TableHead>
              )}
              <TableHead>物品</TableHead>
              <TableHead className="w-[80px]">数量</TableHead>
              <TableHead className="w-[100px]">借用人</TableHead>
              <TableHead className="w-[100px]">操作人</TableHead>
              <TableHead className="w-[100px]">状态</TableHead>
              <TableHead className="hidden md:table-cell">借出时间</TableHead>
              <TableHead className="hidden md:table-cell">预计归还</TableHead>
              <TableHead className="hidden lg:table-cell">归还时间</TableHead>
              {isSuperAdmin && <TableHead className="w-[60px]">操作</TableHead>}
            </TableRow>
          </TableHeader>
          <TableBody>
            {records.map((record) => (
              <TableRow key={record.id} data-state={selectedIds.includes(record.id) ? 'selected' : undefined}>
                {showSelection && (
                  <TableCell>
                    <Checkbox
                      checked={selectedIds.includes(record.id)}
                      onCheckedChange={(checked) => handleSelectOne(record.id, !!checked)}
                    />
                  </TableCell>
                )}
                <TableCell>
                  <Link 
                    href={`/items/${record.item}`}
                    className="text-primary hover:underline"
                  >
                    {record.item_name}
                  </Link>
                  <div className="text-xs text-muted-foreground font-mono">
                    {record.item_sku}
                  </div>
                </TableCell>
                <TableCell className="text-center">
                  {record.quantity ?? 1}
                </TableCell>
                <TableCell>{record.borrower_name}</TableCell>
                <TableCell className="text-muted-foreground">
                  {record.operator_name || record.operator_username || '-'}
                </TableCell>
                <TableCell>
                  <StatusBadge status={record.computed_status} type="borrow" />
                </TableCell>
                <TableCell className="hidden md:table-cell text-muted-foreground">
                  {formatDateTime((record as any).created_at || record.borrowed_at)}
                </TableCell>
                <TableCell className="hidden md:table-cell text-muted-foreground">
                  {((record as any).expected_return_date || record.expected_return_at)
                    ? formatDateTime((record as any).expected_return_date || record.expected_return_at) 
                    : '-'}
                </TableCell>
                <TableCell className="hidden lg:table-cell text-muted-foreground">
                  {((record as any).actual_return_datetime || record.returned_at)
                    ? formatDateTime((record as any).actual_return_datetime || record.returned_at) 
                    : '-'}
                </TableCell>
                {isSuperAdmin && (
                  <TableCell>
                    <Button
                      variant="ghost"
                      size="icon"
                      className="h-8 w-8 text-destructive hover:text-destructive"
                      onClick={() => setDeleteId(record.id)}
                    >
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </TableCell>
                )}
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>
      
      <AlertDialog open={!!deleteId} onOpenChange={(open) => !open && setDeleteId(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>确认删除</AlertDialogTitle>
            <AlertDialogDescription>
              确定要删除这条借用记录吗？此操作无法撤销。
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>取消</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleDelete}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
              disabled={isDeleting}
            >
              {isDeleting ? '删除中...' : '确认删除'}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </>
  );
}

function BorrowRecordTableSkeleton({ showSelection }: { showSelection?: boolean }) {
  return (
    <div className="border rounded-lg overflow-hidden">
      <Table>
        <TableHeader>
          <TableRow>
            {showSelection && <TableHead className="w-[40px]"><Skeleton className="h-4 w-4" /></TableHead>}
            <TableHead>物品</TableHead>
            <TableHead className="w-[100px]">借用人</TableHead>
            <TableHead className="w-[100px]">操作人</TableHead>
            <TableHead className="w-[100px]">状态</TableHead>
            <TableHead className="hidden md:table-cell">借出时间</TableHead>
            <TableHead className="hidden md:table-cell">预计归还</TableHead>
            <TableHead className="hidden lg:table-cell">归还时间</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {Array.from({ length: 10 }).map((_, i) => (
            <TableRow key={i}>
              {showSelection && <TableCell><Skeleton className="h-4 w-4" /></TableCell>}
              <TableCell><Skeleton className="h-4 w-32" /></TableCell>
              <TableCell><Skeleton className="h-4 w-16" /></TableCell>
              <TableCell><Skeleton className="h-4 w-16" /></TableCell>
              <TableCell><Skeleton className="h-5 w-14" /></TableCell>
              <TableCell className="hidden md:table-cell"><Skeleton className="h-4 w-24" /></TableCell>
              <TableCell className="hidden md:table-cell"><Skeleton className="h-4 w-24" /></TableCell>
              <TableCell className="hidden lg:table-cell"><Skeleton className="h-4 w-24" /></TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}
