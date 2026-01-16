'use client';

import { useMemo } from 'react';
import {
  History,
  CheckCircle2,
  XCircle,
  ArrowLeftRight,
  Undo2,
  PackageMinus,
  PackagePlus,
  Trash2,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { ScrollArea } from '@/components/ui/scroll-area';

/**
 * Scan record representing a single scan and action
 */
export interface ScanRecord {
  /** Unique identifier for the record */
  id: string;
  /** Scanned barcode */
  barcode: string;
  /** Item name (if found) */
  itemName: string;
  /** Action performed */
  action: 'borrow' | 'return' | 'take' | 'replenish' | 'lookup';
  /** Result of the action */
  result: 'success' | 'failed';
  /** Timestamp of the scan */
  timestamp: Date;
  /** Optional message */
  message?: string;
}

/**
 * Props for ScanHistory component
 */
export interface ScanHistoryProps {
  /** Array of scan records */
  history: ScanRecord[];
  /** Callback to clear history */
  onClear?: () => void;
  /** Optional className for the container */
  className?: string;
}

/**
 * Action configuration for display
 */
const actionConfig: Record<ScanRecord['action'], { label: string; icon: typeof History }> = {
  borrow: { label: '借出', icon: ArrowLeftRight },
  return: { label: '归还', icon: Undo2 },
  take: { label: '领用', icon: PackageMinus },
  replenish: { label: '补货', icon: PackagePlus },
  lookup: { label: '查询', icon: History },
};

/**
 * Format timestamp to readable string
 */
function formatTime(date: Date): string {
  return date.toLocaleTimeString('zh-CN', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  });
}

/**
 * ScanHistory Component
 * 
 * Displays scan history for the current session with operation summary.
 * 
 * Requirements: 5.3, 5.4
 * - Record scan history for the session
 * - Show operation summary statistics
 */
export function ScanHistory({
  history,
  onClear,
  className,
}: ScanHistoryProps) {
  // Calculate summary statistics (Requirement 5.4)
  const summary = useMemo(() => {
    const stats = {
      total: history.length,
      success: 0,
      failed: 0,
      borrow: 0,
      return: 0,
      take: 0,
      replenish: 0,
    };

    history.forEach((record) => {
      if (record.result === 'success') {
        stats.success++;
      } else {
        stats.failed++;
      }

      if (record.action !== 'lookup') {
        stats[record.action]++;
      }
    });

    return stats;
  }, [history]);

  // Empty state
  if (history.length === 0) {
    return (
      <Card className={cn('', className)}>
        <CardContent className="flex flex-col items-center justify-center py-8 text-center">
          <History className="h-12 w-12 text-muted-foreground/50 mb-4" />
          <p className="text-muted-foreground">暂无扫描记录</p>
          <p className="text-sm text-muted-foreground/70 mt-1">
            扫描条码后，操作记录将显示在这里
          </p>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className={cn('', className)}>
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="text-base flex items-center gap-2">
              <History className="h-4 w-4" />
              扫描历史
            </CardTitle>
            <CardDescription className="mt-1">
              本次会话共 {summary.total} 条记录
            </CardDescription>
          </div>
          {onClear && (
            <Button
              variant="ghost"
              size="sm"
              onClick={onClear}
              className="text-muted-foreground hover:text-destructive"
            >
              <Trash2 className="h-4 w-4" />
            </Button>
          )}
        </div>
      </CardHeader>

      <CardContent className="space-y-4">
        {/* Summary Statistics (Requirement 5.4) */}
        <div className="grid grid-cols-4 gap-2 text-center">
          <div className="rounded-lg bg-muted/50 p-2">
            <div className="text-lg font-semibold text-green-600">{summary.success}</div>
            <div className="text-xs text-muted-foreground">成功</div>
          </div>
          <div className="rounded-lg bg-muted/50 p-2">
            <div className="text-lg font-semibold text-red-600">{summary.failed}</div>
            <div className="text-xs text-muted-foreground">失败</div>
          </div>
          <div className="rounded-lg bg-muted/50 p-2">
            <div className="text-lg font-semibold">{summary.borrow + summary.return}</div>
            <div className="text-xs text-muted-foreground">借还</div>
          </div>
          <div className="rounded-lg bg-muted/50 p-2">
            <div className="text-lg font-semibold">{summary.take + summary.replenish}</div>
            <div className="text-xs text-muted-foreground">领补</div>
          </div>
        </div>

        {/* History List (Requirement 5.3) */}
        <ScrollArea className="h-[200px]">
          <div className="space-y-2">
            {history.map((record) => {
              const config = actionConfig[record.action];
              const Icon = config.icon;
              
              return (
                <div
                  key={record.id}
                  className={cn(
                    'flex items-center gap-3 p-2 rounded-lg border',
                    record.result === 'success'
                      ? 'bg-green-50/50 border-green-200'
                      : 'bg-red-50/50 border-red-200'
                  )}
                >
                  {/* Result Icon */}
                  <div className="flex-shrink-0">
                    {record.result === 'success' ? (
                      <CheckCircle2 className="h-5 w-5 text-green-600" />
                    ) : (
                      <XCircle className="h-5 w-5 text-red-600" />
                    )}
                  </div>

                  {/* Record Info */}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="font-medium text-sm truncate">
                        {record.itemName || record.barcode}
                      </span>
                      <Badge variant="outline" className="text-xs flex-shrink-0">
                        <Icon className="h-3 w-3 mr-1" />
                        {config.label}
                      </Badge>
                    </div>
                    {record.message && (
                      <p className="text-xs text-muted-foreground truncate mt-0.5">
                        {record.message}
                      </p>
                    )}
                  </div>

                  {/* Timestamp */}
                  <div className="text-xs text-muted-foreground flex-shrink-0">
                    {formatTime(record.timestamp)}
                  </div>
                </div>
              );
            })}
          </div>
        </ScrollArea>
      </CardContent>
    </Card>
  );
}
