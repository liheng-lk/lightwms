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
import { useInvoiceCategories, useInvoiceMonths, useInvoiceUploaders } from '@/lib/hooks/use-invoices';

export function InvoiceFilters() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { data: categories } = useInvoiceCategories();
  const { data: months } = useInvoiceMonths();
  const { data: uploaders } = useInvoiceUploaders();

  const currentCategory = searchParams.get('category') || '';
  const currentStatus = searchParams.get('status') || '';
  const currentMonth = searchParams.get('month') || '';
  const currentUploader = searchParams.get('uploader') || '';
  const currentDateFrom = searchParams.get('date_from') || '';
  const currentDateTo = searchParams.get('date_to') || '';
  const currentSearch = searchParams.get('search') || '';

  const updateParams = (key: string, value: string) => {
    const params = new URLSearchParams(searchParams.toString());
    if (value && value !== 'all') {
      params.set(key, value);
    } else {
      params.delete(key);
    }
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
      <Input
        placeholder="搜索发票名称..."
        defaultValue={currentSearch}
        onKeyDown={handleSearch}
        className="w-[200px]"
      />

      <Select value={currentCategory || 'all'} onValueChange={(v) => updateParams('category', v)}>
        <SelectTrigger className="w-[140px]">
          <SelectValue placeholder="所有类别" />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="all">所有类别</SelectItem>
          {categories?.map((cat) => (
            <SelectItem key={cat} value={cat}>{cat}</SelectItem>
          ))}
        </SelectContent>
      </Select>

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

      <Select value={currentMonth || 'all'} onValueChange={(v) => updateParams('month', v)}>
        <SelectTrigger className="w-[140px]">
          <SelectValue placeholder="所有月份" />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="all">所有月份</SelectItem>
          {months?.map((month) => (
            <SelectItem key={month} value={month}>{month}</SelectItem>
          ))}
        </SelectContent>
      </Select>

      <Select value={currentUploader || 'all'} onValueChange={(v) => updateParams('uploader', v)}>
        <SelectTrigger className="w-[160px]">
          <SelectValue placeholder="所有上传者" />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="all">所有上传者</SelectItem>
          {uploaders?.map((uploader) => (
            <SelectItem key={uploader.id} value={String(uploader.id)}>{uploader.username}</SelectItem>
          ))}
        </SelectContent>
      </Select>

      <div className="flex items-center gap-2">
        <Input
          type="date"
          aria-label="开始日期"
          value={currentDateFrom}
          max={currentDateTo || undefined}
          onChange={(e) => updateParams('date_from', e.target.value)}
          className="w-[150px]"
        />
        <span className="text-sm text-muted-foreground">至</span>
        <Input
          type="date"
          aria-label="结束日期"
          value={currentDateTo}
          min={currentDateFrom || undefined}
          onChange={(e) => updateParams('date_to', e.target.value)}
          className="w-[150px]"
        />
      </div>
    </div>
  );
}
