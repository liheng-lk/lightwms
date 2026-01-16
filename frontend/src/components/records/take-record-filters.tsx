'use client';

import { useRouter, useSearchParams } from 'next/navigation';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Label } from '@/components/ui/label';
import { X } from 'lucide-react';

export function TakeRecordFilters() {
  const router = useRouter();
  const searchParams = useSearchParams();
  
  const currentAfter = searchParams.get('taken_after') || '';
  const currentBefore = searchParams.get('taken_before') || '';
  
  const hasFilters = currentAfter || currentBefore;
  
  const updateFilter = (key: string, value: string) => {
    const params = new URLSearchParams(searchParams.toString());
    if (value) {
      params.set(key, value);
    } else {
      params.delete(key);
    }
    params.delete('page');
    router.push(`/take-records?${params.toString()}`);
  };
  
  const clearFilters = () => {
    router.push('/take-records');
  };
  
  return (
    <div className="flex flex-wrap gap-4 items-end">
      {/* 日期范围 */}
      <div className="space-y-1">
        <Label className="text-xs">领用日期从</Label>
        <Input
          type="date"
          value={currentAfter}
          onChange={(e) => updateFilter('taken_after', e.target.value)}
          className="w-[150px]"
        />
      </div>
      
      <div className="space-y-1">
        <Label className="text-xs">到</Label>
        <Input
          type="date"
          value={currentBefore}
          onChange={(e) => updateFilter('taken_before', e.target.value)}
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
