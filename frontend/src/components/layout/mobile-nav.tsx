'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import {
  Package,
  ClipboardList,
  FolderTree,
  MapPin,
  LayoutDashboard,
  PackageMinus,
  PackagePlus,
  Warehouse,
  Users,
  Ticket,
  Settings,
  ScanBarcode,
  FileText,
  Receipt,
} from 'lucide-react';
import {
  SheetContent,
  SheetHeader,
  SheetTitle,
} from '@/components/ui/sheet';
import { cn } from '@/lib/utils';
import { useAuth } from '@/providers/auth-provider';
import { useTheme } from '@/providers/theme-provider';

interface NavItem {
  title: string;
  href: string;
  icon: React.ComponentType<{ className?: string }>;
  roles?: ('super_admin' | 'item_manager')[];
  highlight?: boolean;
}

const navItems: NavItem[] = [
  {
    title: '扫码操作',
    href: '/scan',
    icon: ScanBarcode,
    highlight: true,
  },
  {
    title: '物品管理',
    href: '/items',
    icon: Package,
  },
  {
    title: '借用记录',
    href: '/borrow-records',
    icon: ClipboardList,
  },
  {
    title: '领用记录',
    href: '/take-records',
    icon: PackageMinus,
  },
  {
    title: '补货记录',
    href: '/replenish-records',
    icon: PackagePlus,
  },
  {
    title: '发票管理',
    href: '/invoices',
    icon: Receipt,
  },
  {
    title: '分类管理',
    href: '/categories',
    icon: FolderTree,
    roles: ['super_admin', 'item_manager'],
  },
  {
    title: '库位管理',
    href: '/locations',
    icon: MapPin,
    roles: ['super_admin', 'item_manager'],
  },
  {
    title: '仓库管理',
    href: '/warehouses',
    icon: Warehouse,
    roles: ['super_admin', 'item_manager'],
  },
  {
    title: '审计日志',
    href: '/audit-logs',
    icon: FileText,
    roles: ['super_admin', 'item_manager'],
  },
  {
    title: '用户管理',
    href: '/users',
    icon: Users,
    roles: ['super_admin'],
  },
  {
    title: '邀请码管理',
    href: '/invite-codes',
    icon: Ticket,
    roles: ['super_admin'],
  },
  {
    title: '系统设置',
    href: '/settings',
    icon: Settings,
    roles: ['super_admin'],
  },
];

interface MobileNavProps {
  onClose: () => void;
}

export function MobileNav({ onClose }: MobileNavProps) {
  const pathname = usePathname();
  const { user } = useAuth();
  const { settings } = useTheme();
  
  // 根据角色过滤菜单
  const filteredItems = navItems.filter((item) => {
    if (!item.roles) return true;
    return user?.role && item.roles.includes(user.role);
  });
  
  return (
    <SheetContent side="left" className="w-64 p-0">
      <SheetHeader className="h-16 flex flex-row items-center px-6 border-b">
        <SheetTitle className="flex items-center gap-2">
          {settings.customLogo ? (
            <img
              src={settings.customLogo}
              alt="Logo"
              className="h-8 w-auto max-w-[160px] object-contain"
            />
          ) : (
            <>
              <LayoutDashboard className="h-6 w-6" />
              <span>LightWMS</span>
            </>
          )}
        </SheetTitle>
      </SheetHeader>
      
      <nav className="p-4 space-y-1">
        {filteredItems.map((item) => {
          const isActive = pathname === item.href || pathname.startsWith(`${item.href}/`);
          const Icon = item.icon;
          
          return (
            <Link
              key={item.href}
              href={item.href}
              onClick={onClose}
              className={cn(
                'flex items-center gap-3 px-3 py-2 rounded-md text-sm font-medium transition-colors',
                isActive
                  ? 'bg-primary text-primary-foreground'
                  : item.highlight
                  ? 'bg-primary/10 text-primary hover:bg-primary/20 border border-primary/30'
                  : 'text-muted-foreground hover:bg-muted hover:text-foreground'
              )}
            >
              <Icon className="h-4 w-4" />
              {item.title}
            </Link>
          );
        })}
      </nav>
    </SheetContent>
  );
}
