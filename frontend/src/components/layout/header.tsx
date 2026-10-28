'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { Search, LogOut, User, Menu, ScanBarcode, CircleArrowUp } from 'lucide-react';
import { UpdateNoticeButton, UpdateNoticeDialog, useVersionStatus } from './update-notice';
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
import { MobileNav } from './mobile-nav';
import type { UserRole } from '@/lib/types';

const roleLabels: Record<UserRole, string> = {
  super_admin: '超级管理员',
  item_manager: '物品管理员',
  read_only_user: '普通用户',
};

export function Header() {
  const router = useRouter();
  const { user, logout } = useAuth();
  const [searchKeyword, setSearchKeyword] = useState('');
  const [mobileNavOpen, setMobileNavOpen] = useState(false);

  const [updateDialogOpen, setUpdateDialogOpen] = useState(false);
  const { data: versionStatus } = useVersionStatus(user?.role === 'super_admin');

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

      <UpdateNoticeButton status={versionStatus} onClick={() => setUpdateDialogOpen(true)} />
      <UpdateNoticeDialog open={updateDialogOpen} onOpenChange={setUpdateDialogOpen} status={versionStatus} />

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
            <DropdownMenuItem onClick={() => setUpdateDialogOpen(true)}>
              <CircleArrowUp className="mr-2 h-4 w-4" />
              版本 v{versionStatus.current_version}
              {versionStatus.update_available ? '（有更新）' : ' · 检查更新'}
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
