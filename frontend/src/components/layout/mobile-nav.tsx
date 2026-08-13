'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import {
  Package, ClipboardList, FolderTree, MapPin, LayoutDashboard, PackageMinus,
  PackagePlus, Warehouse, Users, Ticket, Settings, ScanBarcode, FileText, Receipt,
} from 'lucide-react';
import { SheetContent, SheetHeader, SheetTitle } from '@/components/ui/sheet';
import { cn } from '@/lib/utils';
import { useAuth } from '@/providers/auth-provider';
import { useTheme } from '@/providers/theme-provider';

type NavRole = 'super_admin' | 'item_manager' | 'read_only_user';

interface NavItem {
  title: string;
  href: string;
  icon: React.ComponentType<{ className?: string }>;
  roles?: NavRole[];
  highlight?: boolean;
}

const managerRoles: NavRole[] = ['super_admin', 'item_manager'];

const navItems: NavItem[] = [
  { title: '工作台', href: '/', icon: LayoutDashboard },
  { title: '扫码操作', href: '/scan', icon: ScanBarcode, highlight: true },
  { title: '物品管理', href: '/items', icon: Package },
  { title: '借用记录', href: '/borrow-records', icon: ClipboardList },
  { title: '领用记录', href: '/take-records', icon: PackageMinus },
  { title: '补货记录', href: '/replenish-records', icon: PackagePlus, roles: managerRoles },
  { title: '发票管理', href: '/invoices', icon: Receipt, roles: managerRoles },
  { title: '分类管理', href: '/categories', icon: FolderTree, roles: managerRoles },
  { title: '库位管理', href: '/locations', icon: MapPin, roles: managerRoles },
  { title: '仓库管理', href: '/warehouses', icon: Warehouse, roles: managerRoles },
  { title: '审计日志', href: '/audit-logs', icon: FileText, roles: ['super_admin'] },
  { title: '用户管理', href: '/users', icon: Users, roles: ['super_admin'] },
  { title: '邀请码管理', href: '/invite-codes', icon: Ticket, roles: ['super_admin'] },
  { title: '系统设置', href: '/settings', icon: Settings, roles: ['super_admin'] },
];

interface MobileNavProps { onClose: () => void; }

export function MobileNav({ onClose }: MobileNavProps) {
  const pathname = usePathname();
  const { user } = useAuth();
  const { settings } = useTheme();

  const filteredItems = navItems.filter((item) => {
    if (!item.roles) return true;
    return !!user?.role && item.roles.includes(user.role as NavRole);
  });

  return (
    <SheetContent side="left" className="w-72 p-0">
      <SheetHeader className="h-16 flex flex-row items-center px-6 border-b">
        <SheetTitle className="flex items-center gap-2">
          {settings.customLogo ? (
            <img src={settings.customLogo} alt="Logo" className="h-8 w-auto max-w-[160px] object-contain" />
          ) : (
            <><LayoutDashboard className="h-6 w-6" /><span>LightWMS</span></>
          )}
        </SheetTitle>
      </SheetHeader>

      <nav className="p-4 space-y-1" aria-label="移动端主导航">
        {filteredItems.map((item) => {
          const isActive = item.href === '/'
            ? pathname === '/'
            : pathname === item.href || pathname.startsWith(`${item.href}/`);
          const Icon = item.icon;
          return (
            <Link
              key={item.href}
              href={item.href}
              onClick={onClose}
              className={cn(
                'flex min-h-11 items-center gap-3 px-3 py-2 rounded-md text-sm font-medium transition-colors',
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
