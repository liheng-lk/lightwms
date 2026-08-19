'use client';

import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { Search, LogOut, User, Menu, ScanBarcode, CircleArrowUp } from 'lucide-react';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { Sheet, SheetTrigger } from '@/components/ui/sheet';
import { useAuth } from '@/providers/auth-provider';
import { apiFetch } from '@/lib/api/client';
import { MobileNav } from './mobile-nav';
import type { UserRole } from '@/lib/types';

const roleLabels: Record<UserRole, string> = {
  super_admin: '超级管理员',
  item_manager: '物品管理员',
  read_only_user: '普通用户',
};

type VersionStatus = {
  current_version: string;
  latest_version: string | null;
  update_available: boolean;
  check_ok: boolean;
  checked_at: string;
  release_url: string;
  message: string;
};

export function Header() {
  const router = useRouter();
  const { user, logout } = useAuth();
  const [searchKeyword, setSearchKeyword] = useState('');
  const [mobileNavOpen, setMobileNavOpen] = useState(false);

  const { data: versionStatus } = useQuery({
    queryKey: ['system-version'],
    queryFn: () => apiFetch<VersionStatus>('/system-settings/version/'),
    enabled: user?.role === 'super_admin',
    staleTime: 30 * 60 * 1000,
    refetchInterval: 30 * 60 * 1000,
    retry: 1,
  });

  const handleSearch = (event: React.FormEvent) => {
    event.preventDefault();
    if (searchKeyword.trim()) {
      router.push(`/items?keyword=${encodeURIComponent(searchKeyword.trim())}`);
    } else {
      router.push('/items');
    }
  };

  const handleLogout = async () => {
    await logout();
    router.push('/login');
    router.refresh();
  };

  const openReleasePage = () => {
    if (versionStatus?.release_url) {
      window.open(versionStatus.release_url, '_blank', 'noopener,noreferrer');
    }
  };

  return (
    <header className="h-16 border-b bg-background flex items-center gap-4 px-4 md:px-6 sticky top-0 z-30">
      <Sheet open={mobileNavOpen} onOpenChange={setMobileNavOpen}>
        <SheetTrigger asChild>
          <Button variant="ghost" size="icon" className="md:hidden">
            <Menu className="h-5 w-5" />
            <span className="sr-only">打开菜单</span>
          </Button>
        </SheetTrigger>
        <MobileNav onClose={() => setMobileNavOpen(false)} />
      </Sheet>

      <form onSubmit={handleSearch} className="flex-1 max-w-xl">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="搜索物品名称、SKU 或条码..."
            value={searchKeyword}
            onChange={(event) => setSearchKeyword(event.target.value)}
            className="pl-10"
          />
        </div>
      </form>

      {versionStatus?.update_available && versionStatus.latest_version && (
        <Button
          variant="outline"
          size="sm"
          onClick={openReleasePage}
          title={`当前 ${versionStatus.current_version}，最新 ${versionStatus.latest_version}`}
          className="hidden sm:flex"
        >
          <CircleArrowUp className="h-4 w-4 mr-2" />
          新版本 v{versionStatus.latest_version}
        </Button>
      )}

      <Link href="/scan" className="md:hidden">
        <Button variant="outline" size="icon" className="border-primary/50 text-primary hover:bg-primary/10">
          <ScanBarcode className="h-5 w-5" />
          <span className="sr-only">扫码</span>
        </Button>
      </Link>

      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <Button variant="ghost" className="gap-2">
            <User className="h-4 w-4" />
            <span className="hidden sm:inline">{user?.username}</span>
            <span className="hidden lg:inline text-xs text-muted-foreground">
              ({user?.role ? roleLabels[user.role] : ''})
            </span>
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end">
          {user?.role === 'super_admin' && versionStatus?.current_version && (
            <DropdownMenuItem disabled>
              当前版本 v{versionStatus.current_version}
            </DropdownMenuItem>
          )}
          <DropdownMenuItem onClick={handleLogout}>
            <LogOut className="mr-2 h-4 w-4" />
            退出登录
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>
    </header>
  );
}
