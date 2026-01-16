'use client';

import { useRouter, useSearchParams } from 'next/navigation';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Button } from '@/components/ui/button';
import { X } from 'lucide-react';
import { useCategoryList } from '@/lib/hooks/use-trees';
import { useLocationList } from '@/lib/hooks/use-trees';

const statusOptions = [
  { value: 'available', label: '可用' },
  { value: 'borrowed', label: '已借出' },
  { value: 'in_stock', label: '有库存' },
  { value: 'out_of_stock', label: '缺货' },
];

const typeOptions = [
  { value: 'unique', label: '唯一物品' },
  { value: 'consumable', label: '消耗品' },
];

export function ItemFilters() {
  const router = useRouter();
  const searchParams = useSearchParams();
  
  const { data: categories } = useCategoryList();
  const { data: locations } = useLocationList();
  
  const currentCategory = searchParams.get('category') || 'all';
  const currentLocation = searchParams.get('location') || 'all';
  const currentStatus = searchParams.get('status') || 'all';
  const currentType = searchParams.get('type') || 'all';
  
  const hasFilters = currentCategory || currentLocation || currentStatus || currentType;
  
  const updateFilter = (key: string, value: string) => {
    const params = new URLSearchParams(searchParams.toString());
    if (value && value !== 'all') {
      params.set(key, value);
    } else {
      params.delete(key);
    }
    params.delete('page'); // 重置页码
    router.push(`/items?${params.toString()}`);
  };
  
  const clearFilters = () => {
    const params = new URLSearchParams();
    const keyword = searchParams.get('keyword');
    if (keyword) params.set('keyword', keyword);
    router.push(`/items?${params.toString()}`);
  };
  
  return (
    <div className="flex flex-wrap gap-3 items-center">
      {/* 分类筛选 */}
      <Select value={currentCategory} onValueChange={(v) => updateFilter('category', v)}>
        <SelectTrigger className="w-[140px]">
          <SelectValue placeholder="选择分类" />
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
      
      {/* 库位筛选 */}
      <Select value={currentLocation} onValueChange={(v) => updateFilter('location', v)}>
        <SelectTrigger className="w-[140px]">
          <SelectValue placeholder="选择库位" />
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
      
      {/* 状态筛选 */}
      <Select value={currentStatus} onValueChange={(v) => updateFilter('status', v)}>
        <SelectTrigger className="w-[120px]">
          <SelectValue placeholder="状态" />
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
      
      {/* 类型筛选 */}
      <Select value={currentType} onValueChange={(v) => updateFilter('type', v)}>
        <SelectTrigger className="w-[120px]">
          <SelectValue placeholder="类型" />
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
      
      {/* 清除筛选 */}
      {hasFilters && (
        <Button variant="ghost" size="sm" onClick={clearFilters}>
          <X className="h-4 w-4 mr-1" />
          清除筛选
        </Button>
      )}
    </div>
  );
}
