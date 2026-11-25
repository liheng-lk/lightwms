'use client';

import { useMemo } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';

interface DataPoint {
  month: string;
  count: number;
}

interface InventoryTrendChartProps {
  data: DataPoint[];
  borrowData?: DataPoint[];
  isLoading?: boolean;
}

/** Readable Chinese month labels. */
function formatMonth(monthStr: string): string {
  const [, month] = monthStr.split('-');
  return `${parseInt(month, 10)}月`;
}

const COLORS = {
  inventory: 'hsl(var(--primary))',
  borrow: 'hsl(var(--chart-2, 220 70% 55%))',
  grid: 'hsl(var(--border))',
  text: 'hsl(var(--muted-foreground))',
};

export function InventoryTrendChart({ data, borrowData, isLoading }: InventoryTrendChartProps) {
  const chartData = useMemo(() => {
    if (!data.length) return { points: [], borrowPoints: [] as DataPoint[], maxY: 0, labels: [] };

    const borrowPointsArr: DataPoint[] = borrowData ?? [];
    const allValues = [
      ...data.map((d) => d.count),
      ...borrowPointsArr.map((d) => d.count),
    ];
    const maxY = Math.max(...allValues, 1);

    return {
      points: data,
      borrowPoints: borrowPointsArr,
      maxY,
      labels: data.map((d) => formatMonth(d.month)),
    };
  }, [data, borrowData]);

  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-base">库存与借用趋势</CardTitle>
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
          <CardTitle className="text-base">库存与借用趋势</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="h-[200px] flex items-center justify-center text-muted-foreground text-sm">
            暂无数据
          </div>
        </CardContent>
      </Card>
    );
  }

  const { points, borrowPoints, maxY, labels } = chartData;
  const width = 100;
  const height = 50;
  const paddingX = 8;
  const paddingY = 4;
  const plotW = width - paddingX * 2;
  const plotH = height - paddingY * 2;

  function toX(i: number) {
    return paddingX + (i / Math.max(points.length - 1, 1)) * plotW;
  }
  function toY(v: number) {
    return paddingY + plotH - (v / maxY) * plotH;
  }

  const inventoryPath = points
    .map((p, i) => `${i === 0 ? 'M' : 'L'} ${toX(i).toFixed(2)} ${toY(p.count).toFixed(2)}`)
    .join(' ');

  const borrowPath =
    borrowPoints.length > 0
      ? borrowPoints
          .map((p, i) => `${i === 0 ? 'M' : 'L'} ${toX(i).toFixed(2)} ${toY(p.count).toFixed(2)}`)
          .join(' ')
      : '';

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-base">库存与借用趋势</CardTitle>
        <div className="flex gap-4 text-xs text-muted-foreground">
          <span className="flex items-center gap-1">
            <span className="inline-block w-3 h-0.5 rounded" style={{ background: COLORS.inventory }} />
            新增物品
          </span>
          {borrowPoints.length > 0 && (
            <span className="flex items-center gap-1">
              <span className="inline-block w-3 h-0.5 rounded" style={{ background: COLORS.borrow }} />
              借用记录
            </span>
          )}
        </div>
      </CardHeader>
      <CardContent>
        <svg
          viewBox={`0 0 ${width} ${height + 6}`}
          className="w-full h-auto"
          style={{ maxHeight: 220 }}
          preserveAspectRatio="xMidYMid meet"
        >
          {/* Grid lines */}
          {[0, 0.25, 0.5, 0.75, 1].map((frac) => {
            const y = paddingY + plotH - frac * plotH;
            return (
              <line
                key={frac}
                x1={paddingX}
                x2={width - paddingX}
                y1={y}
                y2={y}
                stroke={COLORS.grid}
                strokeWidth={0.15}
                strokeDasharray="0.5"
              />
            );
          })}

          {/* Y-axis labels */}
          {[0, 0.5, 1].map((frac) => {
            const y = paddingY + plotH - frac * plotH;
            const val = Math.round(maxY * frac);
            return (
              <text
                key={frac}
                x={paddingX - 1}
                y={y + 0.5}
                fill={COLORS.text}
                fontSize={2.5}
                textAnchor="end"
              >
                {val}
              </text>
            );
          })}

          {/* Inventory line */}
          <path d={inventoryPath} fill="none" stroke={COLORS.inventory} strokeWidth={0.5} />
          {points.map((p, i) => (
            <circle
              key={`inv-${i}`}
              cx={toX(i)}
              cy={toY(p.count)}
              r={0.6}
              fill={COLORS.inventory}
            />
          ))}

          {/* Borrow line */}
          {borrowPath && (
            <>
              <path
                d={borrowPath}
                fill="none"
                stroke={COLORS.borrow}
                strokeWidth={0.5}
                strokeDasharray="1"
              />
              {borrowPoints.map((p, i) => (
                <circle
                  key={`bor-${i}`}
                  cx={toX(i)}
                  cy={toY(p.count)}
                  r={0.6}
                  fill={COLORS.borrow}
                />
              ))}
            </>
          )}

          {/* X-axis labels */}
          {labels.map((label, i) => (
            <text
              key={i}
              x={toX(i)}
              y={height + 3}
              fill={COLORS.text}
              fontSize={2.5}
              textAnchor="middle"
            >
              {label}
            </text>
          ))}
        </svg>
      </CardContent>
    </Card>
  );
}
