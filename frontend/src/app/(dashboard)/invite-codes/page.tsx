'use client';

import { useState, useCallback } from 'react';
import { useSearchParams, useRouter } from 'next/navigation';
import { ChevronLeft, ChevronRight, Plus } from 'lucide-react';
import { Button } from '@/components/ui/button';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { InviteCodeTable } from '@/components/invite-codes/invite-code-table';
import { InviteCodeForm } from '@/components/invite-codes/invite-code-form';
import { PageHelp } from '@/components/ui/help-tooltip';
import { useInviteCodes } from '@/lib/hooks/use-invite-codes';

const PAGE_SIZES = [10, 20, 50];

export default function InviteCodesPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [showCreateForm, setShowCreateForm] = useState(false);
  
  // Get params from URL
  const page = Number(searchParams.get('page')) || 1;
  const page_size = Number(searchParams.get('page_size')) || 20;
  
  // Fetch invite codes - Requirements 19.1
  const { data, isLoading, refetch } = useInviteCodes({
    page,
    page_size,
  });
  
  const totalPages = data ? Math.ceil(data.count / page_size) : 0;
  
  const updateParams = useCallback((updates: Record<string, string | number | undefined>) => {
    const params = new URLSearchParams(searchParams.toString());
    Object.entries(updates).forEach(([key, value]) => {
      if (value !== undefined && value !== '') {
        params.set(key, String(value));
      } else {
        params.delete(key);
      }
    });
    router.push(`/invite-codes?${params.toString()}`);
  }, [searchParams, router]);
  
  const goToPage = (newPage: number) => {
    updateParams({ page: newPage });
  };
  
  const changePageSize = (newSize: string) => {
    updateParams({ page_size: Number(newSize), page: 1 });
  };

  const handleCreateSuccess = () => {
    refetch();
  };

  const handleDeactivateSuccess = () => {
    refetch();
  };
  
  return (
    <div className="space-y-4">
      {/* Page Header - Requirements 19.1 */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <h1 className="text-2xl font-semibold">邀请码管理</h1>
          <PageHelp
            title="邀请码管理使用指南"
            tips={[
              '邀请码用于邀请新用户注册系统',
              '每个邀请码可设置最大使用次数',
              '可为邀请码设置默认角色和过期时间',
              '点击复制按钮可复制注册链接',
              '停用后的邀请码无法再用于注册',
            ]}
          />
        </div>
        {/* Create Button - Requirements 19.2 */}
        <Button onClick={() => setShowCreateForm(true)}>
          <Plus className="h-4 w-4 mr-2" />
          新增邀请码
        </Button>
      </div>
      
      {/* Invite Code Table - Requirements 19.1 */}
      <InviteCodeTable 
        inviteCodes={data?.results || []} 
        isLoading={isLoading}
        onDeactivateSuccess={handleDeactivateSuccess}
      />
      
      {/* Pagination */}
      {data && data.count > 0 && (
        <div className="flex items-center justify-between">
          <div className="text-sm text-muted-foreground">
            共 {data.count} 条，第 {page} / {totalPages} 页
          </div>
          
          <div className="flex items-center gap-4">
            {/* Page Size Selector */}
            <div className="flex items-center gap-2">
              <span className="text-sm text-muted-foreground">每页</span>
              <Select value={String(page_size)} onValueChange={changePageSize}>
                <SelectTrigger className="w-[70px]">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {PAGE_SIZES.map((size) => (
                    <SelectItem key={size} value={String(size)}>
                      {size}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <span className="text-sm text-muted-foreground">条</span>
            </div>
            
            {/* Page Navigation */}
            <div className="flex items-center gap-1">
              <Button
                variant="outline"
                size="icon"
                onClick={() => goToPage(page - 1)}
                disabled={page <= 1}
              >
                <ChevronLeft className="h-4 w-4" />
              </Button>
              <Button
                variant="outline"
                size="icon"
                onClick={() => goToPage(page + 1)}
                disabled={page >= totalPages}
              >
                <ChevronRight className="h-4 w-4" />
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* Create Invite Code Form - Requirements 19.2, 19.3 */}
      <InviteCodeForm
        open={showCreateForm}
        onOpenChange={setShowCreateForm}
        onSuccess={handleCreateSuccess}
      />
    </div>
  );
}
