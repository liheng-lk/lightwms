'use client';

import { useMemo } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';

interface TopItem {
  name: string;
  sku: string;
  borrow_count: number;
}

interface BorrowStatsChartProps {
  data: TopItem[];
  isLoading?: boolean;
}

const BAR_COLOR = 'hsl(var(--primary))';
const TEXT_COLOR = 'hsl(var(--muted-foreground))';

export function BorrowStatsChart({ data, isLoading }: BorrowStatsChartProps) {
  const chartItems = useMemo(() => {
    if (!data.length) return { items: [], maxCount: 0 };
    const items = data.slice(0, 8); // show top 8
    const maxCount = Math.max(...items.map((d) => d.borrow_count), 1);
    return { items, maxCount };
  }, [data]);

  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-base">热门借用物品</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="h-[200px] flex items-center justify-center text-muted-foreground text-sm">
            加载中...
          </div>
        </CardContent>
      </Card>
    );
  }

  if (!data.length) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-base">热门借用物品</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="h-[200px] flex items-center justify-center text-muted-foreground text-sm">
            暂无借用数据
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-base">热门借用物品</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-2">
          {chartItems.items.map((item, i) => {
            const pct = (item.borrow_count / chartItems.maxCount) * 100;
            return (
              <div key={item.sku} className="flex items-center gap-3">
                <span className="w-4 text-right text-xs text-muted-foreground tabular-nums">
                  {i + 1}
                </span>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center justify-between mb-0.5">
                    <span className="text-sm truncate" title={item.name}>
                      {item.name}
                    </span>
                    <span className="text-xs text-muted-foreground tabular-nums ml-2 shrink-0">
                      {item.borrow_count}次
                    </span>
                  </div>
                  <div className="h-1.5 w-full rounded-full bg-muted overflow-hidden">
                    <div
                      className="h-full rounded-full transition-all"
                      style={{
                        width: `${pct}%`,
                        background: BAR_COLOR,
                      }}
                    />
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </CardContent>
    </Card>
  );
}
