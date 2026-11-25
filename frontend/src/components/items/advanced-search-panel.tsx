'use client';

import { useState, useCallback, useEffect } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { ChevronDown, ChevronUp, Search, X, Save } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Card, CardContent } from '@/components/ui/card';
import { useCategoryList, useLocationList } from '@/lib/hooks/use-trees';
import { useUsers } from '@/lib/hooks/use-users';
import { useAuth } from '@/providers/auth-provider';

const statusOptions = [
  { value: 'available', label: '可用' },
  { value: 'borrowed', label: '已借出' },
  { value: 'in_stock', label: '有库存' },
  { value: 'out_of_stock', label: '缺货' },
];

const typeOptions = [
  { value: 'reusable', label: '可重复使用' },
  { value: 'consumable', label: '消耗品' },
];

const STORAGE_KEY = 'lightwms_advanced_search';

interface SearchConditions {
  keyword: string;
  category: string;
  location: string;
  status: string;
  type: string;
  owner: string;
  date_from: string;
  date_to: string;
  quantity_min: string;
  quantity_max: string;
}

const defaultConditions: SearchConditions = {
  keyword: '',
  category: '',
  location: '',
  status: '',
  type: '',
  owner: '',
  date_from: '',
  date_to: '',
  quantity_min: '',
  quantity_max: '',
};

function loadSavedConditions(): SearchConditions | null {
  try {
    const saved = localStorage.getItem(STORAGE_KEY);
    if (saved) {
      return JSON.parse(saved) as SearchConditions;
    }
  } catch {
    // ignore parse errors
  }
  return null;
}

function saveConditions(conditions: SearchConditions) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(conditions));
  } catch {
    // ignore storage errors
  }
}

export function AdvancedSearchPanel() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { user } = useAuth();
  const [expanded, setExpanded] = useState(false);

  // Initialize from URL params
  const [conditions, setConditions] = useState<SearchConditions>(() => ({
    keyword: searchParams.get('keyword') || '',
    category: searchParams.get('category') || '',
    location: searchParams.get('location') || '',
    status: searchParams.get('status') || '',
    type: searchParams.get('type') || '',
    owner: searchParams.get('owner') || '',
    date_from: searchParams.get('date_from') || '',
    date_to: searchParams.get('date_to') || '',
    quantity_min: searchParams.get('quantity_min') || '',
    quantity_max: searchParams.get('quantity_max') || '',
  }));

  const { data: categories } = useCategoryList();
  const { data: locations } = useLocationList();
  const { data: usersData } = useUsers({ page_size: 100 });

  const isSuperAdmin = user?.role === 'super_admin';
  const isItemManager = user?.role === 'item_manager';
  const canFilterOwner = isSuperAdmin || isItemManager;

  const updateCondition = useCallback((key: keyof SearchConditions, value: string) => {
    setConditions((prev) => ({ ...prev, [key]: value }));
  }, []);

  const hasAdvancedFilters =
    conditions.owner ||
    conditions.date_from ||
    conditions.date_to ||
    conditions.quantity_min ||
    conditions.quantity_max;

  const hasAnyFilter = Object.values(conditions).some((v) => v !== '');

  const handleSearch = useCallback(() => {
    const params = new URLSearchParams();
    for (const [key, value] of Object.entries(conditions)) {
      if (value && value !== 'all') {
        params.set(key, value);
      }
    }
    params.delete('page'); // Reset to page 1
    router.push(`/items?${params.toString()}`);
  }, [conditions, router]);

  const handleClear = useCallback(() => {
    setConditions(defaultConditions);
    router.push('/items');
  }, [router]);

  const handleSave = useCallback(() => {
    saveConditions(conditions);
  }, [conditions]);

  const handleLoadSaved = useCallback(() => {
    const saved = loadSavedConditions();
    if (saved) {
      setConditions(saved);
    }
  }, []);

  // Keyboard shortcut: Enter to search
  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === 'Enter') {
        handleSearch();
      }
    },
    [handleSearch],
  );

  // Auto-expand if advanced filters are active from URL
  useEffect(() => {
    if (hasAdvancedFilters) {
      setExpanded(true);
    }
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <Card>
      <CardContent className="p-4">
        {/* Basic search row */}
        <div className="flex flex-wrap gap-3 items-end" onKeyDown={handleKeyDown}>
          {/* 关键词搜索 */}
          <div className="flex-1 min-w-[200px]">
            <Label className="text-xs mb-1 block text-muted-foreground">关键词</Label>
            <Input
              placeholder="名称、SKU、条码..."
              value={conditions.keyword}
              onChange={(e) => updateCondition('keyword', e.target.value)}
            />
          </div>

          {/* 分类 */}
          <div className="w-[140px]">
            <Label className="text-xs mb-1 block text-muted-foreground">分类</Label>
            <Select
              value={conditions.category || 'all'}
              onValueChange={(v) => updateCondition('category', v === 'all' ? '' : v)}
            >
              <SelectTrigger>
                <SelectValue placeholder="全部分类" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">全部分类</SelectItem>
                {categories?.map((cat) => (
                  <SelectItem key={cat.id} value={String(cat.id)}>
                    {cat.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {/* 库位 */}
          <div className="w-[140px]">
            <Label className="text-xs mb-1 block text-muted-foreground">库位</Label>
            <Select
              value={conditions.location || 'all'}
              onValueChange={(v) => updateCondition('location', v === 'all' ? '' : v)}
            >
              <SelectTrigger>
                <SelectValue placeholder="全部库位" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">全部库位</SelectItem>
                {locations?.map((loc) => (
                  <SelectItem key={loc.id} value={String(loc.id)}>
                    {loc.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {/* 状态 */}
          <div className="w-[120px]">
            <Label className="text-xs mb-1 block text-muted-foreground">状态</Label>
            <Select
              value={conditions.status || 'all'}
              onValueChange={(v) => updateCondition('status', v === 'all' ? '' : v)}
            >
              <SelectTrigger>
                <SelectValue placeholder="全部状态" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">全部状态</SelectItem>
                {statusOptions.map((opt) => (
                  <SelectItem key={opt.value} value={opt.value}>
                    {opt.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {/* 类型 */}
          <div className="w-[120px]">
            <Label className="text-xs mb-1 block text-muted-foreground">类型</Label>
            <Select
              value={conditions.type || 'all'}
              onValueChange={(v) => updateCondition('type', v === 'all' ? '' : v)}
            >
              <SelectTrigger>
                <SelectValue placeholder="全部类型" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">全部类型</SelectItem>
                {typeOptions.map((opt) => (
                  <SelectItem key={opt.value} value={opt.value}>
                    {opt.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {/* Action buttons */}
          <div className="flex items-center gap-2">
            <Button size="sm" onClick={handleSearch}>
              <Search className="h-4 w-4 mr-1" />
              搜索
            </Button>
            <Button
              size="sm"
              variant="ghost"
              onClick={() => setExpanded(!expanded)}
              className="text-muted-foreground"
            >
              {expanded ? (
                <>
                  <ChevronUp className="h-4 w-4 mr-1" />
                  收起
                </>
              ) : (
                <>
                  <ChevronDown className="h-4 w-4 mr-1" />
                  高级
                </>
              )}
            </Button>
          </div>
        </div>

        {/* Advanced filters (collapsible) */}
        {expanded && (
          <div className="mt-4 pt-4 border-t" onKeyDown={handleKeyDown}>
            <div className="flex flex-wrap gap-3 items-end">
              {/* 负责人 */}
              {canFilterOwner && (
                <div className="w-[140px]">
                  <Label className="text-xs mb-1 block text-muted-foreground">负责人</Label>
                  <Select
                    value={conditions.owner || 'all'}
                    onValueChange={(v) => updateCondition('owner', v === 'all' ? '' : v)}
                  >
                    <SelectTrigger>
                      <SelectValue placeholder="全部" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="all">全部</SelectItem>
                      {usersData?.results?.map((u) => (
                        <SelectItem key={u.id} value={String(u.id)}>
                          {u.username}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              )}

              {/* 创建日期范围 */}
              <div className="w-[150px]">
                <Label className="text-xs mb-1 block text-muted-foreground">创建日期（从）</Label>
                <Input
                  type="date"
                  value={conditions.date_from}
                  onChange={(e) => updateCondition('date_from', e.target.value)}
                />
              </div>
              <div className="w-[150px]">
                <Label className="text-xs mb-1 block text-muted-foreground">创建日期（到）</Label>
                <Input
                  type="date"
                  value={conditions.date_to}
                  onChange={(e) => updateCondition('date_to', e.target.value)}
                />
              </div>

              {/* 数量范围 */}
              <div className="w-[120px]">
                <Label className="text-xs mb-1 block text-muted-foreground">数量下限</Label>
                <Input
                  type="number"
                  min={0}
                  placeholder="最小"
                  value={conditions.quantity_min}
                  onChange={(e) => updateCondition('quantity_min', e.target.value)}
                />
              </div>
              <div className="w-[120px]">
                <Label className="text-xs mb-1 block text-muted-foreground">数量上限</Label>
                <Input
                  type="number"
                  min={0}
                  placeholder="最大"
                  value={conditions.quantity_max}
                  onChange={(e) => updateCondition('quantity_max', e.target.value)}
                />
              </div>
            </div>

            {/* Save/load/clear row */}
            <div className="flex items-center gap-2 mt-3">
              <Button size="sm" variant="outline" onClick={handleSave}>
                <Save className="h-3.5 w-3.5 mr-1" />
                保存条件
              </Button>
              <Button size="sm" variant="outline" onClick={handleLoadSaved}>
                加载已保存
              </Button>
              {hasAnyFilter && (
                <Button size="sm" variant="ghost" onClick={handleClear}>
                  <X className="h-3.5 w-3.5 mr-1" />
                  清除全部
                </Button>
              )}
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
