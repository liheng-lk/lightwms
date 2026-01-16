'use client';

import { useSearchParams, useRouter } from 'next/navigation';
import { useState } from 'react';
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
import { ChevronLeft, ChevronRight, Download, Trash2, X } from 'lucide-react';
import { BorrowRecordFilters } from '@/components/records/borrow-record-filters';
import { BorrowRecordTable } from '@/components/records/borrow-record-table';
import { PageHelp } from '@/components/ui/help-tooltip';
import { useBorrowRecords, exportBorrowRecords, useDeleteBorrowRecords } from '@/lib/hooks/use-records';
import { usePermissions } from '@/lib/hooks/use-permissions';

const PAGE_SIZES = [10, 20, 50];

export default function BorrowRecordsPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [isExporting, setIsExporting] = useState(false);
  const [selectedIds, setSelectedIds] = useState<number[]>([]);
  const [showDeleteDialog, setShowDeleteDialog] = useState(false);
  const { isSuperAdmin } = usePermissions();
  const { mutate: batchDelete, isPending: isDeleting } = useDeleteBorrowRecords();
  
  const status = searchParams.get('status') || undefined;
  const borrowed_after = searchParams.get('borrowed_after') || undefined;
  const borrowed_before = searchParams.get('borrowed_before') || undefined;
  const page = Number(searchParams.get('page')) || 1;
  const page_size = Number(searchParams.get('page_size')) || 20;
  
  const { data, isLoading } = useBorrowRecords({
    status,
    borrowed_after,
    borrowed_before,
    page,
    page_size,
  });
  
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
    router.push(`/borrow-records?${params.toString()}`);
  };
  
  const goToPage = (newPage: number) => {
    updateParams({ page: newPage });
  };
  
  const changePageSize = (newSize: string) => {
    updateParams({ page_size: Number(newSize), page: 1 });
  };

  const handleExport = async () => {
    setIsExporting(true);
    try {
      const blob = await exportBorrowRecords({
        status,
        borrowed_after,
        borrowed_before,
      });
      
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `借用记录_${new Date().toISOString().split('T')[0]}.xlsx`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (error) {
      console.error('Export failed:', error);
    } finally {
      setIsExporting(false);
    }
  };

  const handleBatchDelete = () => {
    batchDelete(selectedIds, {
      onSuccess: () => {
        setSelectedIds([]);
        setShowDeleteDialog(false);
      },
    });
  };
  
  return (
    <div className="space-y-4">
      {/* 页面标题 */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <h1 className="text-2xl font-semibold">借出记录</h1>
          <PageHelp
            title="借出记录使用指南"
            tips={[
              '查看所有物品的借出和归还记录',
              '按状态筛选：借出中、已逾期、已归还',
              '按日期范围筛选特定时间段的记录',
              '逾期记录会以红色标识提醒',
              '点击物品名称可跳转到物品详情',
              '支持导出 Excel 文件',
            ]}
          />
        </div>
        <Button
          variant="outline"
          size="sm"
          onClick={handleExport}
          disabled={isExporting || !data?.count}
        >
          <Download className="h-4 w-4 mr-2" />
          {isExporting ? '导出中...' : '导出 Excel'}
        </Button>
      </div>

      {/* 批量操作栏 */}
      {isSuperAdmin && selectedIds.length > 0 && (
        <div className="flex items-center gap-4 p-3 bg-muted rounded-lg">
          <span className="text-sm">已选择 {selectedIds.length} 条记录</span>
          <Button
            variant="destructive"
            size="sm"
            onClick={() => setShowDeleteDialog(true)}
          >
            <Trash2 className="h-4 w-4 mr-2" />
            批量删除
          </Button>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setSelectedIds([])}
          >
            <X className="h-4 w-4 mr-2" />
            取消选择
          </Button>
        </div>
      )}
      
      {/* 筛选器 */}
      <BorrowRecordFilters />
      
      {/* 记录表格 */}
      <BorrowRecordTable
        records={data?.results || []}
        isLoading={isLoading}
        selectedIds={selectedIds}
        onSelectionChange={setSelectedIds}
      />
      
      {/* 分页 */}
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
                    <SelectItem key={size} value={String(size)}>
                      {size}
                    </SelectItem>
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

      {/* 批量删除确认对话框 */}
      <AlertDialog open={showDeleteDialog} onOpenChange={setShowDeleteDialog}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>确认批量删除</AlertDialogTitle>
            <AlertDialogDescription>
              确定要删除选中的 {selectedIds.length} 条借用记录吗？此操作无法撤销。
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>取消</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleBatchDelete}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
              disabled={isDeleting}
            >
              {isDeleting ? '删除中...' : '确认删除'}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
