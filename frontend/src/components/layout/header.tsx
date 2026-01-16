'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { Search, LogOut, User, Menu, ScanBarcode } from 'lucide-react';
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

const roleLabels = {
  super_admin: '超级管理员',
  item_manager: '物品管理员',
};

export function Header() {
  const router = useRouter();
  const { user, logout } = useAuth();
  const [searchKeyword, setSearchKeyword] = useState('');
  const [mobileNavOpen, setMobileNavOpen] = useState(false);
  
  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    if (searchKeyword.trim()) {
      router.push(`/items?keyword=${encodeURIComponent(searchKeyword.trim())}`);
    } else {
      // 清空搜索框时，跳转到物品列表（不带 keyword 参数）
      router.push('/items');
    }
  };
  
  const handleLogout = async () => {
    await logout();
    router.push('/login');
  };
  
  return (
    <header className="h-16 border-b bg-background px-4 md:px-6 flex items-center justify-between gap-4">
      {/* Mobile menu button */}
      <Sheet open={mobileNavOpen} onOpenChange={setMobileNavOpen}>
        <SheetTrigger asChild>
          <Button variant="ghost" size="icon" className="md:hidden">
            <Menu className="h-5 w-5" />
            <span className="sr-only">打开菜单</span>
          </Button>
        </SheetTrigger>
        <MobileNav onClose={() => setMobileNavOpen(false)} />
      </Sheet>
      
      {/* 全局搜索框 */}
      <form onSubmit={handleSearch} className="flex-1 max-w-md">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            type="search"
            placeholder="搜索物品（SKU/条码/名称）..."
            value={searchKeyword}
            onChange={(e) => setSearchKeyword(e.target.value)}
            className="pl-10"
          />
        </div>
      </form>
      
      {/* 移动端扫码按钮 */}
      <Link href="/scan" className="md:hidden">
        <Button variant="outline" size="icon" className="border-primary/50 text-primary hover:bg-primary/10">
          <ScanBarcode className="h-5 w-5" />
          <span className="sr-only">扫码</span>
        </Button>
      </Link>
      
      {/* 用户菜单 */}
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
          <DropdownMenuItem onClick={handleLogout}>
            <LogOut className="mr-2 h-4 w-4" />
            退出登录
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>
    </header>
  );
}
