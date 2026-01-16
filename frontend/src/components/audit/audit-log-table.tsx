'use client';

import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog';
import { ScrollArea } from '@/components/ui/scroll-area';
import { ChevronLeft, ChevronRight, Eye } from 'lucide-react';
import { AuditLog, ACTION_LABELS, TARGET_TYPE_LABELS } from '@/lib/api/audit';
import { format } from 'date-fns';
import { zhCN } from 'date-fns/locale';

interface AuditLogTableProps {
  logs: AuditLog[];
  isLoading: boolean;
  page: number;
  totalPages: number;
  totalCount: number;
  onPageChange: (page: number) => void;
}

function getActionBadgeVariant(action: string): 'default' | 'secondary' | 'destructive' | 'outline' {
  switch (action) {
    case 'create':
      return 'default';
    case 'update':
      return 'secondary';
    case 'delete':
    case 'deactivate':
      return 'destructive';
    case 'borrow':
    case 'return':
    case 'take':
    case 'replenish':
      return 'outline';
    default:
      return 'secondary';
  }
}

function DiffViewer({ diff }: { diff: AuditLog['diff'] }) {
  if (!diff || (Object.keys(diff.before || {}).length === 0 && Object.keys(diff.after || {}).length === 0)) {
    return <span className="text-muted-foreground">无变更详情</span>;
  }

  return (
    <div className="space-y-4">
      {diff.before && Object.keys(diff.before).length > 0 && (
        <div>
          <h4 className="font-medium text-sm mb-2 text-red-600">变更前</h4>
          <pre className="bg-red-50 dark:bg-red-950/20 p-3 rounded text-xs overflow-auto">
            {JSON.stringify(diff.before, null, 2)}
          </pre>
        </div>
      )}
      {diff.after && Object.keys(diff.after).length > 0 && (
        <div>
          <h4 className="font-medium text-sm mb-2 text-green-600">变更后</h4>
          <pre className="bg-green-50 dark:bg-green-950/20 p-3 rounded text-xs overflow-auto">
            {JSON.stringify(diff.after, null, 2)}
          </pre>
        </div>
      )}
    </div>
  );
}

export function AuditLogTable({
  logs,
  isLoading,
  page,
  totalPages,
  totalCount,
  onPageChange,
}: AuditLogTableProps) {
  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
      </div>
    );
  }

  if (logs.length === 0) {
    return (
      <div className="flex items-center justify-center h-64 text-muted-foreground">
        暂无审计日志
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="rounded-md border">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="w-[160px]">时间</TableHead>
              <TableHead className="w-[100px]">操作用户</TableHead>
              <TableHead className="w-[80px]">操作</TableHead>
              <TableHead className="w-[100px]">目标类型</TableHead>
              <TableHead className="w-[80px]">目标ID</TableHead>
              <TableHead className="w-[120px]">IP地址</TableHead>
              <TableHead className="w-[80px]">详情</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {logs.map((log) => (
              <TableRow key={log.id}>
                <TableCell className="text-sm">
                  {format(new Date(log.created_at), 'yyyy-MM-dd HH:mm:ss', { locale: zhCN })}
                </TableCell>
                <TableCell>
                  <span className="font-medium">{log.operator_username || '系统'}</span>
                </TableCell>
                <TableCell>
                  <Badge variant={getActionBadgeVariant(log.action)}>
                    {ACTION_LABELS[log.action] || log.action}
                  </Badge>
                </TableCell>
                <TableCell>
                  {TARGET_TYPE_LABELS[log.target_type] || log.target_type}
                </TableCell>
                <TableCell className="font-mono text-sm">
                  {log.target_id}
                </TableCell>
                <TableCell className="text-sm text-muted-foreground">
                  {log.ip || '-'}
                </TableCell>
                <TableCell>
                  <Dialog>
                    <DialogTrigger asChild>
                      <Button variant="ghost" size="sm">
                        <Eye className="h-4 w-4" />
                      </Button>
                    </DialogTrigger>
                    <DialogContent className="max-w-2xl">
                      <DialogHeader>
                        <DialogTitle>操作详情</DialogTitle>
                      </DialogHeader>
                      <ScrollArea className="max-h-[60vh]">
                        <div className="space-y-4 p-1">
                          <div className="grid grid-cols-2 gap-4 text-sm">
                            <div>
                              <span className="text-muted-foreground">操作时间：</span>
                              {format(new Date(log.created_at), 'yyyy-MM-dd HH:mm:ss', { locale: zhCN })}
                            </div>
                            <div>
                              <span className="text-muted-foreground">操作用户：</span>
                              {log.operator_username || '系统'}
                            </div>
                            <div>
                              <span className="text-muted-foreground">用户角色：</span>
                              {log.operator_role || '-'}
                            </div>
                            <div>
                              <span className="text-muted-foreground">IP地址：</span>
                              {log.ip || '-'}
                            </div>
                          </div>
                          <div className="text-sm">
                            <span className="text-muted-foreground">User Agent：</span>
                            <p className="mt-1 text-xs break-all">{log.user_agent || '-'}</p>
                          </div>
                          <div className="border-t pt-4">
                            <h4 className="font-medium mb-2">变更内容</h4>
                            <DiffViewer diff={log.diff} />
                          </div>
                        </div>
                      </ScrollArea>
                    </DialogContent>
                  </Dialog>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>

      {/* Pagination */}
      <div className="flex items-center justify-between">
        <div className="text-sm text-muted-foreground">
          共 {totalCount} 条记录
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => onPageChange(page - 1)}
            disabled={page <= 1}
          >
            <ChevronLeft className="h-4 w-4" />
            上一页
          </Button>
          <span className="text-sm">
            第 {page} / {totalPages} 页
          </span>
          <Button
            variant="outline"
            size="sm"
            onClick={() => onPageChange(page + 1)}
            disabled={page >= totalPages}
          >
            下一页
            <ChevronRight className="h-4 w-4" />
          </Button>
        </div>
      </div>
    </div>
  );
}
