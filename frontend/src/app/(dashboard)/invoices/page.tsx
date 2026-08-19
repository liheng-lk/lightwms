'use client';

import { useState } from 'react';
import { useSearchParams, useRouter } from 'next/navigation';
import { Plus, Download, FileSpreadsheet, ChevronLeft, ChevronRight, X, Trash2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
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
import { InvoiceFilters } from '@/components/invoices/invoice-filters';
import { InvoiceTable } from '@/components/invoices/invoice-table';
import { InvoiceForm } from '@/components/invoices/invoice-form';
import { InvoiceStatusDialog } from '@/components/invoices/invoice-status-dialog';
import { PageHelp } from '@/components/ui/help-tooltip';
import {
  useInvoices,
  useExportInvoices,
  useExportInvoicesByIds,
  useExportReimbursementExcel,
  useBatchUpdateInvoiceStatus,
  useBatchDeleteInvoices,
} from '@/lib/hooks/use-invoices';
import { usePermissions } from '@/lib/hooks/use-permissions';
import type { Invoice } from '@/lib/types';

const PAGE_SIZES = [10, 20, 50];

export default function InvoicesPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { canCreate, isSuperAdmin } = usePermissions();

  const [showCreateDialog, setShowCreateDialog] = useState(false);
  const [editingInvoice, setEditingInvoice] = useState<Invoice | undefined>();
  const [statusInvoice, setStatusInvoice] = useState<Invoice | undefined>();
  const [selectedIds, setSelectedIds] = useState<number[]>([]);
  const [showBatchDeleteDialog, setShowBatchDeleteDialog] = useState(false);
  const [batchStatusValue, setBatchStatusValue] = useState<string>('');

  const category = searchParams.get('category') || undefined;
  const status = searchParams.get('status') || undefined;
  const month = searchParams.get('month') || undefined;
  const uploader = searchParams.get('uploader') || undefined;
  const date_from = searchParams.get('date_from') || undefined;
  const date_to = searchParams.get('date_to') || undefined;
  const search = searchParams.get('search') || undefined;
  const page = Number(searchParams.get('page')) || 1;
  const page_size = Number(searchParams.get('page_size')) || 20;

  const filterParams = {
    category,
    status,
    month,
    uploader,
    date_from,
    date_to,
    search,
  };

  const { data, isLoading, refetch } = useInvoices({
    ...filterParams,
    page,
    page_size,
  });

  const exportMutation = useExportInvoices();
  const exportByIdsMutation = useExportInvoicesByIds();
  const reimbursementExportMutation = useExportReimbursementExcel();
  const batchStatusMutation = useBatchUpdateInvoiceStatus();
  const batchDeleteMutation = useBatchDeleteInvoices();

  const totalPages = data ? Math.ceil(data.count / page_size) : 0;

  const updateParams = (updates: Record<string, string | number | undefined>) => {
    const params = new URLSearchParams(searchParams.toString());
    Object.entries(updates).forEach(([key, value]) => {
      if (value !== undefined && value !== '') {
        params.set(key, String(value));
      } else {
        params.delete(key);
      }
    });
    router.push(`/invoices?${params.toString()}`);
  };

  const goToPage = (newPage: number) => updateParams({ page: newPage });
  const changePageSize = (newSize: string) => updateParams({ page_size: Number(newSize), page: 1 });

  const handleExport = () => {
    if (selectedIds.length > 0) {
      exportByIdsMutation.mutate(selectedIds, {
        onSuccess: () => setSelectedIds([]),
      });
    } else {
      exportMutation.mutate(filterParams);
    }
  };

  const handleReimbursementExport = () => {
    reimbursementExportMutation.mutate(filterParams);
  };

  const handleClearSelection = () => setSelectedIds([]);

  const handleBatchStatusChange = (newStatus: string) => {
    if (!isSuperAdmin || selectedIds.length === 0) return;
    batchStatusMutation.mutate(
      { ids: selectedIds, status: newStatus },
      {
        onSuccess: () => {
          setSelectedIds([]);
          setBatchStatusValue('');
          refetch();
        },
      }
    );
  };

  const handleBatchDelete = () => {
    if (!isSuperAdmin || selectedIds.length === 0) return;
    batchDeleteMutation.mutate(selectedIds, {
      onSuccess: () => {
        setSelectedIds([]);
        setShowBatchDeleteDialog(false);
        refetch();
      },
    });
  };

  const handleSuccess = () => refetch();

  const handleEditDialogClose = (open: boolean) => {
    if (!open) setEditingInvoice(undefined);
  };

  const handleStatusDialogClose = (open: boolean) => {
    if (!open) setStatusInvoice(undefined);
  };

  // Reimbursement approval and bulk destructive actions are system-level
  // administration. Item Managers can still list/create/edit/delete individual
  // inventory invoices globally, but cannot approve reimbursement state.
  const canBatchOperate = isSuperAdmin;

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between gap-4">
        <div className="flex items-center gap-2">
          <h1 className="text-2xl font-semibold">发票管理</h1>
          <PageHelp
            title="发票管理使用指南"
            tips={[
              '物品管理员可查看、登记和编辑全部库存相关发票',
              '在新增物品时也可以同时上传发票',
              '可按类别、状态、月份、上传者和自定义日期范围筛选',
              '发票文件 ZIP 和报销清单 Excel 会继承当前筛选条件',
              '报销状态审批及批量操作仅超级管理员可操作',
            ]}
          />
        </div>
        <div className="flex flex-wrap items-center justify-end gap-2">
          {isSuperAdmin && (
            <>
              <Button
                variant="outline"
                onClick={handleExport}
                disabled={exportMutation.isPending || exportByIdsMutation.isPending}
              >
                <Download className="h-4 w-4 mr-2" />
                {exportMutation.isPending || exportByIdsMutation.isPending
                  ? '导出中...'
                  : selectedIds.length > 0
                    ? `导出选中 (${selectedIds.length})`
                    : '发票文件 ZIP'}
              </Button>
              <Button
                variant="outline"
                onClick={handleReimbursementExport}
                disabled={reimbursementExportMutation.isPending}
              >
                <FileSpreadsheet className="h-4 w-4 mr-2" />
                {reimbursementExportMutation.isPending ? '导出中...' : '报销清单 Excel'}
              </Button>
            </>
          )}
          {canCreate() && (
            <Button onClick={() => setShowCreateDialog(true)}>
              <Plus className="h-4 w-4 mr-2" />
              新增发票
            </Button>
          )}
        </div>
      </div>

      {selectedIds.length > 0 && canBatchOperate && (
        <div className="flex items-center gap-4 p-3 bg-muted rounded-lg">
          <span className="text-sm">
            已选择 <strong>{selectedIds.length}</strong> 张发票
          </span>
          <Select value={batchStatusValue} onValueChange={handleBatchStatusChange}>
            <SelectTrigger className="w-[140px]">
              <SelectValue placeholder="批量改状态" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="pending">未报销</SelectItem>
              <SelectItem value="reimbursed">已报销</SelectItem>
              <SelectItem value="rejected">无法报销</SelectItem>
            </SelectContent>
          </Select>
          <Button
            variant="outline"
            size="sm"
            onClick={() => setShowBatchDeleteDialog(true)}
            className="text-destructive hover:text-destructive"
          >
            <Trash2 className="h-4 w-4 mr-1" />
            批量删除
          </Button>
          <Button variant="ghost" size="sm" onClick={handleClearSelection}>
            <X className="h-4 w-4 mr-1" />
            取消选择
          </Button>
        </div>
      )}

      <InvoiceFilters />

      <InvoiceTable
        invoices={data?.results || []}
        isLoading={isLoading}
        onEdit={setEditingInvoice}
        onStatusChange={isSuperAdmin ? setStatusInvoice : undefined}
        selectable={canBatchOperate}
        selectedIds={selectedIds}
        onSelectionChange={canBatchOperate ? setSelectedIds : undefined}
      />

      {data && data.count > 0 && (
        <div className="flex items-center justify-between">
          <div className="text-sm text-muted-foreground">
            共 {data.count} 条，第 {page} / {totalPages} 页
          </div>
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2">
              <span className="text-sm text-muted-foreground">每页</span>
              <Select value={String(page_size)} onValueChange={changePageSize}>
                <SelectTrigger className="w-[70px]">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {PAGE_SIZES.map((size) => (
                    <SelectItem key={size} value={String(size)}>{size}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <span className="text-sm text-muted-foreground">条</span>
            </div>
            <div className="flex items-center gap-1">
              <Button
                variant="outline"
                size="icon"
                onClick={() => goToPage(page - 1)}
                disabled={page <= 1}
              >
                <ChevronLeft className="h-4 w-4" />
              </Button>
              <Button
                variant="outline"
                size="icon"
                onClick={() => goToPage(page + 1)}
                disabled={page >= totalPages}
              >
                <ChevronRight className="h-4 w-4" />
              </Button>
            </div>
          </div>
        </div>
      )}

      <InvoiceForm
        open={showCreateDialog}
        onOpenChange={setShowCreateDialog}
        onSuccess={handleSuccess}
      />
      <InvoiceForm
        invoice={editingInvoice}
        open={!!editingInvoice}
        onOpenChange={handleEditDialogClose}
        onSuccess={handleSuccess}
      />
      {isSuperAdmin && (
        <InvoiceStatusDialog
          invoice={statusInvoice}
          open={!!statusInvoice}
          onOpenChange={handleStatusDialogClose}
          onSuccess={handleSuccess}
        />
      )}

      {isSuperAdmin && (
        <AlertDialog open={showBatchDeleteDialog} onOpenChange={setShowBatchDeleteDialog}>
          <AlertDialogContent>
            <AlertDialogHeader>
              <AlertDialogTitle>确认批量删除</AlertDialogTitle>
              <AlertDialogDescription>
                确定要删除选中的 {selectedIds.length} 张发票吗？此操作无法撤销。
              </AlertDialogDescription>
            </AlertDialogHeader>
            <AlertDialogFooter>
              <AlertDialogCancel>取消</AlertDialogCancel>
              <AlertDialogAction
                onClick={handleBatchDelete}
                disabled={batchDeleteMutation.isPending}
                className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
              >
                {batchDeleteMutation.isPending ? '删除中...' : '确认删除'}
              </AlertDialogAction>
            </AlertDialogFooter>
          </AlertDialogContent>
        </AlertDialog>
      )}
    </div>
  );
}
