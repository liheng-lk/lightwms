'use client';

import { useRouter, useSearchParams } from 'next/navigation';
import { Input } from '@/components/ui/input';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { useInvoiceCategories, useInvoiceMonths } from '@/lib/hooks/use-invoices';

export function InvoiceFilters() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { data: categories } = useInvoiceCategories();
  const { data: months } = useInvoiceMonths();

  const currentCategory = searchParams.get('category') || '';
  const currentStatus = searchParams.get('status') || '';
  const currentMonth = searchParams.get('month') || '';
  const currentSearch = searchParams.get('search') || '';

  const updateParams = (key: string, value: string) => {
    const params = new URLSearchParams(searchParams.toString());
    if (value && value !== 'all') {
      params.set(key, value);
    } else {
      params.delete(key);
    }
    // Reset to page 1 when filters change
    params.delete('page');
    router.push(`/invoices?${params.toString()}`);
  };

  const handleSearch = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') {
      const value = (e.target as HTMLInputElement).value.trim();
      updateParams('search', value);
    }
  };

  return (
    <div className="flex flex-wrap gap-3">
      {/* 搜索 */}
      <Input
        placeholder="搜索发票名称..."
        defaultValue={currentSearch}
        onKeyDown={handleSearch}
        className="w-[200px]"
      />

      {/* 类别筛选 */}
      <Select value={currentCategory || 'all'} onValueChange={(v) => updateParams('category', v)}>
        <SelectTrigger className="w-[140px]">
          <SelectValue placeholder="所有类别" />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="all">所有类别</SelectItem>
          {categories?.map((cat) => (
            <SelectItem key={cat} value={cat}>
              {cat}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>

      {/* 状态筛选 */}
      <Select value={currentStatus || 'all'} onValueChange={(v) => updateParams('status', v)}>
        <SelectTrigger className="w-[140px]">
          <SelectValue placeholder="所有状态" />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="all">所有状态</SelectItem>
          <SelectItem value="pending">未报销</SelectItem>
          <SelectItem value="reimbursed">已报销</SelectItem>
          <SelectItem value="rejected">无法报销</SelectItem>
        </SelectContent>
      </Select>

      {/* 月份筛选 */}
      <Select value={currentMonth || 'all'} onValueChange={(v) => updateParams('month', v)}>
        <SelectTrigger className="w-[140px]">
          <SelectValue placeholder="所有月份" />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="all">所有月份</SelectItem>
          {months?.map((month) => (
            <SelectItem key={month} value={month}>
              {month}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </div>
  );
}
