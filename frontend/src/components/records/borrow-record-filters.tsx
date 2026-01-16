'use client';

import { useRouter, useSearchParams } from 'next/navigation';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Label } from '@/components/ui/label';
import { X } from 'lucide-react';

const statusOptions = [
  { value: 'active', label: '借出中' },
  { value: 'overdue', label: '已逾期' },
  { value: 'returned', label: '已归还' },
];

export function BorrowRecordFilters() {
  const router = useRouter();
  const searchParams = useSearchParams();
  
  const currentStatus = searchParams.get('status') || 'all';
  const currentAfter = searchParams.get('borrowed_after') || '';
  const currentBefore = searchParams.get('borrowed_before') || '';
  
  const hasFilters = currentStatus || currentAfter || currentBefore;
  
  const updateFilter = (key: string, value: string) => {
    const params = new URLSearchParams(searchParams.toString());
    if (value && value !== 'all') {
      params.set(key, value);
    } else {
      params.delete(key);
    }
    params.delete('page');
    router.push(`/borrow-records?${params.toString()}`);
  };
  
  const clearFilters = () => {
    router.push('/borrow-records');
  };
  
  return (
    <div className="flex flex-wrap gap-4 items-end">
      {/* 状态筛选 */}
      <div className="space-y-1">
        <Label className="text-xs">状态</Label>
        <Select value={currentStatus} onValueChange={(v) => updateFilter('status', v)}>
          <SelectTrigger className="w-[120px]">
            <SelectValue placeholder="全部" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">全部</SelectItem>
            {statusOptions.map((opt) => (
              <SelectItem key={opt.value} value={opt.value}>
                {opt.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>
      
      {/* 日期范围 */}
      <div className="space-y-1">
        <Label className="text-xs">借出日期从</Label>
        <Input
          type="date"
          value={currentAfter}
          onChange={(e) => updateFilter('borrowed_after', e.target.value)}
          className="w-[150px]"
        />
      </div>
      
      <div className="space-y-1">
        <Label className="text-xs">到</Label>
        <Input
          type="date"
          value={currentBefore}
          onChange={(e) => updateFilter('borrowed_before', e.target.value)}
          className="w-[150px]"
        />
      </div>
      
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
