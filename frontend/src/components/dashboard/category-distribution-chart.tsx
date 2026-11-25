'use client';

import { useMemo } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';

interface CategoryData {
  name: string;
  count: number;
}

interface CategoryDistributionChartProps {
  data: CategoryData[];
  isLoading?: boolean;
}

const PALETTE = [
  'hsl(var(--primary))',
  'hsl(var(--chart-2, 220 70% 55%))',
  'hsl(var(--chart-3, 150 60% 45%))',
  'hsl(var(--chart-4, 30 80% 55%))',
  'hsl(var(--chart-5, 280 60% 55%))',
  'hsl(340 65% 55%)',
  'hsl(190 70% 50%)',
  'hsl(60 60% 48%)',
];

export function CategoryDistributionChart({ data, isLoading }: CategoryDistributionChartProps) {
  const chartData = useMemo(() => {
    if (!data.length) return { slices: [], total: 0 };

    const total = data.reduce((sum, d) => sum + d.count, 0);
    if (total === 0) return { slices: [], total: 0 };

    // Take top categories, merge rest into "其他"
    const sorted = [...data].sort((a, b) => b.count - a.count);
    let top = sorted.slice(0, 7);
    const rest = sorted.slice(7);
    if (rest.length > 0) {
      const restCount = rest.reduce((s, d) => s + d.count, 0);
      top = [...top, { name: '其他', count: restCount }];
    }

    let startAngle = 0;
    const slices = top.map((item, i) => {
      const angle = (item.count / total) * 360;
      const slice = {
        name: item.name,
        count: item.count,
        pct: ((item.count / total) * 100).toFixed(1),
        color: PALETTE[i % PALETTE.length],
        startAngle,
        endAngle: startAngle + angle,
      };
      startAngle += angle;
      return slice;
    });

    return { slices, total };
  }, [data]);

  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-base">分类分布</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="h-[200px] flex items-center justify-center text-muted-foreground text-sm">
            加载中...
          </div>
        </CardContent>
      </Card>
    );
  }

  if (!data.length || chartData.total === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-base">分类分布</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="h-[200px] flex items-center justify-center text-muted-foreground text-sm">
            暂无分类数据
          </div>
        </CardContent>
      </Card>
    );
  }

  const cx = 50;
  const cy = 50;
  const r = 40;

  function polarToCartesian(angleInDegrees: number) {
    const rad = ((angleInDegrees - 90) * Math.PI) / 180;
    return {
      x: cx + r * Math.cos(rad),
      y: cy + r * Math.sin(rad),
    };
  }

  function arcPath(startAngle: number, endAngle: number) {
    const start = polarToCartesian(endAngle);
    const end = polarToCartesian(startAngle);
    const largeArc = endAngle - startAngle > 180 ? 1 : 0;

    return [
      `M ${cx} ${cy}`,
      `L ${start.x.toFixed(2)} ${start.y.toFixed(2)}`,
      `A ${r} ${r} 0 ${largeArc} 0 ${end.x.toFixed(2)} ${end.y.toFixed(2)}`,
      'Z',
    ].join(' ');
  }

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-base">分类分布</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="flex flex-col sm:flex-row items-center gap-4">
          {/* Pie chart */}
          <svg
            viewBox="0 0 100 100"
            className="w-32 h-32 sm:w-40 sm:h-40 shrink-0"
            style={{ maxWidth: 160 }}
          >
            {chartData.slices.map((slice) => {
              // Handle full circle
              if (slice.endAngle - slice.startAngle >= 359.99) {
                return (
                  <circle
                    key={slice.name}
                    cx={cx}
                    cy={cy}
                    r={r}
                    fill={slice.color}
                  />
                );
              }
              return (
                <path
                  key={slice.name}
                  d={arcPath(slice.startAngle, slice.endAngle)}
                  fill={slice.color}
                  stroke="hsl(var(--background))"
                  strokeWidth={0.5}
                >
                  <title>{`${slice.name}: ${slice.count} (${slice.pct}%)`}</title>
                </path>
              );
            })}
          </svg>

          {/* Legend */}
          <div className="flex flex-wrap gap-x-4 gap-y-1.5 text-xs sm:text-sm">
            {chartData.slices.map((slice) => (
              <div key={slice.name} className="flex items-center gap-1.5">
                <span
                  className="inline-block w-2.5 h-2.5 rounded-sm shrink-0"
                  style={{ background: slice.color }}
                />
                <span className="text-muted-foreground">
                  {slice.name}
                  <span className="ml-1 tabular-nums">({slice.count})</span>
                </span>
              </div>
            ))}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
