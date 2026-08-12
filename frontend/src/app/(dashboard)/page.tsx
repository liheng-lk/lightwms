'use client';

import { useEffect, useMemo, useState } from 'react';
import Link from 'next/link';
import {
  AlertTriangle,
  ArrowRight,
  ClipboardList,
  Package,
  PackageMinus,
  ScanBarcode,
} from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';

interface DashboardMetrics {
  items: number | null;
  activeBorrows: number | null;
  outOfStock: number | null;
  todayTakes: number | null;
}

interface PaginatedResponse {
  count?: number;
  results?: unknown[];
}

const initialMetrics: DashboardMetrics = {
  items: null,
  activeBorrows: null,
  outOfStock: null,
  todayTakes: null,
};

function localDateString() {
  const now = new Date();
  const year = now.getFullYear();
  const month = String(now.getMonth() + 1).padStart(2, '0');
  const day = String(now.getDate()).padStart(2, '0');
  return `${year}-${month}-${day}`;
}

async function fetchCount(path: string): Promise<number> {
  const response = await fetch(path, { cache: 'no-store' });
  if (!response.ok) {
    throw new Error(`Request failed: ${response.status}`);
  }
  const data = (await response.json()) as PaginatedResponse | unknown[];
  if (Array.isArray(data)) return data.length;
  if (typeof data.count === 'number') return data.count;
  return Array.isArray(data.results) ? data.results.length : 0;
}

export default function DashboardPage() {
  const [metrics, setMetrics] = useState<DashboardMetrics>(initialMetrics);
  const [loading, setLoading] = useState(true);
  const [hasPartialError, setHasPartialError] = useState(false);

  const today = useMemo(localDateString, []);

  useEffect(() => {
    let cancelled = false;

    async function loadDashboard() {
      setLoading(true);
      setHasPartialError(false);

      const requests = await Promise.allSettled([
        fetchCount('/api/wms/items/?page_size=1'),
        fetchCount('/api/wms/borrow-records/?status=active&page_size=1'),
        fetchCount('/api/wms/items/?type=consumable&status=out_of_stock&page_size=1'),
        fetchCount(`/api/wms/take-records/?start_date=${today}&end_date=${today}&page_size=1`),
      ]);

      if (cancelled) return;

      const value = (index: number) =>
        requests[index].status === 'fulfilled' ? requests[index].value : null;

      setMetrics({
        items: value(0),
        activeBorrows: value(1),
        outOfStock: value(2),
        todayTakes: value(3),
      });
      setHasPartialError(requests.some((result) => result.status === 'rejected'));
      setLoading(false);
    }

    void loadDashboard();
    return () => {
      cancelled = true;
    };
  }, [today]);

  const metricCards = [
    {
      label: '在库物品',
      value: metrics.items,
      description: '当前启用的全部物品',
      href: '/items',
      icon: Package,
    },
    {
      label: '当前借用',
      value: metrics.activeBorrows,
      description: '尚未完成归还的借用记录',
      href: '/borrow-records?status=active',
      icon: ClipboardList,
    },
    {
      label: '缺货耗材',
      value: metrics.outOfStock,
      description: '库存已归零，需要关注补货',
      href: '/items?type=consumable&status=out_of_stock',
      icon: AlertTriangle,
    },
    {
      label: '今日领用',
      value: metrics.todayTakes,
      description: '今天发生的耗材领用记录',
      href: `/take-records?start_date=${today}&end_date=${today}`,
      icon: PackageMinus,
    },
  ];

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">工作台</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            先处理异常，再执行高频操作，避免在多个记录页面之间来回寻找。
          </p>
        </div>
        <Button asChild size="lg" className="min-h-11 sm:min-h-10">
          <Link href="/scan">
            <ScanBarcode className="mr-2 h-5 w-5" />
            扫码操作
          </Link>
        </Button>
      </div>

      {hasPartialError && (
        <div className="flex items-start gap-3 rounded-lg border border-amber-500/30 bg-amber-500/10 px-4 py-3 text-sm">
          <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-amber-600" />
          <div>
            <p className="font-medium">部分统计暂时无法读取</p>
            <p className="text-muted-foreground">不影响扫码、借还和库存操作，可稍后刷新工作台。</p>
          </div>
        </div>
      )}

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {metricCards.map((metric) => {
          const Icon = metric.icon;
          return (
            <Link key={metric.label} href={metric.href} className="group rounded-xl focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring">
              <Card className="h-full transition-colors group-hover:border-primary/40">
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                  <CardTitle className="text-sm font-medium">{metric.label}</CardTitle>
                  <Icon className="h-4 w-4 text-muted-foreground" />
                </CardHeader>
                <CardContent>
                  <div className="text-3xl font-semibold tabular-nums">
                    {loading || metric.value === null ? '—' : metric.value}
                  </div>
                  <p className="mt-1 text-xs text-muted-foreground">{metric.description}</p>
                </CardContent>
              </Card>
            </Link>
          );
        })}
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>高频操作</CardTitle>
            <CardDescription>仓库现场优先走最短路径，减少重复搜索和页面跳转。</CardDescription>
          </CardHeader>
          <CardContent className="grid gap-3 sm:grid-cols-2">
            <Button asChild variant="outline" className="h-auto min-h-14 justify-between px-4 py-3">
              <Link href="/scan">
                <span className="flex items-center gap-3">
                  <ScanBarcode className="h-5 w-5" />
                  扫码借还/领补
                </span>
                <ArrowRight className="h-4 w-4" />
              </Link>
            </Button>
            <Button asChild variant="outline" className="h-auto min-h-14 justify-between px-4 py-3">
              <Link href="/items">
                <span className="flex items-center gap-3">
                  <Package className="h-5 w-5" />
                  查找物品
                </span>
                <ArrowRight className="h-4 w-4" />
              </Link>
            </Button>
            <Button asChild variant="outline" className="h-auto min-h-14 justify-between px-4 py-3">
              <Link href="/borrow-records?status=active">
                <span className="flex items-center gap-3">
                  <ClipboardList className="h-5 w-5" />
                  处理未归还
                </span>
                <ArrowRight className="h-4 w-4" />
              </Link>
            </Button>
            <Button asChild variant="outline" className="h-auto min-h-14 justify-between px-4 py-3">
              <Link href="/items?type=consumable&status=out_of_stock">
                <span className="flex items-center gap-3">
                  <AlertTriangle className="h-5 w-5" />
                  查看缺货耗材
                </span>
                <ArrowRight className="h-4 w-4" />
              </Link>
            </Button>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>使用建议</CardTitle>
            <CardDescription>按真实仓库现场的操作优先级组织，而不是按数据库模块组织。</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4 text-sm">
            <div className="flex gap-3">
              <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-primary/10 text-xs font-semibold text-primary">1</div>
              <div>
                <p className="font-medium">有条码时直接扫码</p>
                <p className="text-muted-foreground">借用、归还、领用和补货不需要先进入物品列表。</p>
              </div>
            </div>
            <div className="flex gap-3">
              <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-primary/10 text-xs font-semibold text-primary">2</div>
              <div>
                <p className="font-medium">先处理缺货和未归还</p>
                <p className="text-muted-foreground">工作台把需要关注的状态放在普通管理操作之前。</p>
              </div>
            </div>
            <div className="flex gap-3">
              <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-primary/10 text-xs font-semibold text-primary">3</div>
              <div>
                <p className="font-medium">管理配置放到低频区域</p>
                <p className="text-muted-foreground">仓库、库位、分类和系统设置不应干扰日常出入库路径。</p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
