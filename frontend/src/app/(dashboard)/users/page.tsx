'use client';

import { useState, useCallback } from 'react';
import { useSearchParams, useRouter } from 'next/navigation';
import { ChevronLeft, ChevronRight, Copy, Check, Plus } from 'lucide-react';
import { Button } from '@/components/ui/button';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog';
import { UserTable } from '@/components/users/user-table';
import { UserFilters } from '@/components/users/user-filters';
import { UserForm } from '@/components/users/user-form';
import { SetPasswordDialog } from '@/components/users/set-password-dialog';
import { UpdateRoleDialog } from '@/components/users/update-role-dialog';
import { PageHelp } from '@/components/ui/help-tooltip';
import { useUsers, useResetPassword } from '@/lib/hooks/use-users';
import type { User, UserRole } from '@/lib/types';
import { copyText } from '@/lib/clipboard';
import { toast } from 'sonner';

const PAGE_SIZES = [10, 20, 50];

export default function UsersPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  
  // Create user state
  const [showCreateUser, setShowCreateUser] = useState(false);
  
  // Set password state
  const [setPasswordUser, setSetPasswordUser] = useState<User | null>(null);
  const [showSetPassword, setShowSetPassword] = useState(false);
  
  // Update role state
  const [updateRoleUser, setUpdateRoleUser] = useState<User | null>(null);
  const [showUpdateRole, setShowUpdateRole] = useState(false);
  
  // Reset password state
  const [resetPasswordUser, setResetPasswordUser] = useState<User | null>(null);
  const [showResetConfirm, setShowResetConfirm] = useState(false);
  const [temporaryPassword, setTemporaryPassword] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);
  
  // Get params from URL
  const page = Number(searchParams.get('page')) || 1;
  const page_size = Number(searchParams.get('page_size')) || 20;
  const search = searchParams.get('search') || '';
  const role = searchParams.get('role') || '';
  const status = searchParams.get('is_active') || '';
  
  // Fetch users with filters - Requirements 18.1, 18.2
  const { data, isLoading, refetch } = useUsers({
    page,
    page_size,
    search: search || undefined,
    role: (role && role !== 'all' ? role : undefined) as UserRole | undefined,
    is_active: status && status !== 'all' ? status === 'true' : undefined,
  });
  
  const { mutate: resetPasswordMutation, isPending: isResetting } = useResetPassword();
  
  const totalPages = data ? Math.ceil(data.count / page_size) : 0;
  
  const updateParams = useCallback((updates: Record<string, string | number | undefined>) => {
    const params = new URLSearchParams(searchParams.toString());
    Object.entries(updates).forEach(([key, value]) => {
      if (value !== undefined && value !== '' && value !== 'all') {
        params.set(key, String(value));
      } else {
        params.delete(key);
      }
    });
    router.push(`/users?${params.toString()}`);
  }, [searchParams, router]);
  
  const goToPage = (newPage: number) => {
    updateParams({ page: newPage });
  };
  
  const changePageSize = (newSize: string) => {
    updateParams({ page_size: Number(newSize), page: 1 });
  };

  const handleSearchChange = (value: string) => {
    updateParams({ search: value, page: 1 });
  };

  const handleRoleChange = (value: string) => {
    updateParams({ role: value, page: 1 });
  };

  const handleStatusChange = (value: string) => {
    updateParams({ is_active: value, page: 1 });
  };

  const handleClearFilters = () => {
    router.push('/users');
  };

  const handleDisableSuccess = () => {
    refetch();
  };

  // Set password handlers
  const handleSetPasswordClick = (user: User) => {
    setSetPasswordUser(user);
    setShowSetPassword(true);
  };

  // Update role handlers
  const handleUpdateRoleClick = (user: User) => {
    setUpdateRoleUser(user);
    setShowUpdateRole(true);
  };

  // Reset password handlers - Requirements 18.4
  const handleResetPasswordClick = (user: User) => {
    setResetPasswordUser(user);
    setShowResetConfirm(true);
  };

  const handleResetPasswordConfirm = () => {
    if (!resetPasswordUser) return;
    
    resetPasswordMutation(resetPasswordUser.id, {
      onSuccess: (data) => {
        setShowResetConfirm(false);
        setTemporaryPassword(data.temporary_password);
      },
    });
  };

  const handleCopyPassword = async () => {
    if (temporaryPassword) {
      if (await copyText(temporaryPassword)) {
        setCopied(true);
        setTimeout(() => setCopied(false), 2000);
      } else {
        toast.error('浏览器不允许自动复制，请手动选中临时密码复制');
      }
    }
  };

  const handleClosePasswordDialog = () => {
    setTemporaryPassword(null);
    setResetPasswordUser(null);
    setCopied(false);
  };
  
  return (
    <div className="space-y-4">
      {/* Page Header - Requirements 18.1 */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <h1 className="text-2xl font-semibold">用户管理</h1>
          <PageHelp
            title="用户管理使用指南"
            tips={[
              '查看系统中所有注册用户',
              '可按角色和状态筛选用户',
              '点击「添加用户」直接创建新用户',
              '点击「修改角色」调整用户权限',
              '点击「设置密码」为用户设置新密码',
              '点击「重置密码」生成临时密码',
              '点击「禁用」可禁止用户登录',
              '仅超级管理员可管理用户',
            ]}
          />
        </div>
        <Button onClick={() => setShowCreateUser(true)}>
          <Plus className="h-4 w-4 mr-2" />
          添加用户
        </Button>
      </div>
      
      {/* Filters - Requirements 18.2 */}
      <UserFilters
        search={search}
        role={role}
        status={status}
        onSearchChange={handleSearchChange}
        onRoleChange={handleRoleChange}
        onStatusChange={handleStatusChange}
        onClear={handleClearFilters}
      />
      
      {/* User Table - Requirements 18.1 */}
      <UserTable 
        users={data?.results || []} 
        isLoading={isLoading} 
        onResetPassword={handleResetPasswordClick}
        onSetPassword={handleSetPasswordClick}
        onUpdateRole={handleUpdateRoleClick}
        onDisableSuccess={handleDisableSuccess}
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

      {/* Reset Password Confirmation Dialog - Requirements 18.4 */}
      <AlertDialog open={showResetConfirm} onOpenChange={setShowResetConfirm}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>确认重置密码</AlertDialogTitle>
            <AlertDialogDescription>
              确定要重置用户「{resetPasswordUser?.username}」的密码吗？
              重置后将生成一个临时密码，请妥善保管。
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>取消</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleResetPasswordConfirm}
              disabled={isResetting}
            >
              {isResetting ? '重置中...' : '确认重置'}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      {/* Temporary Password Display Dialog - Requirements 18.4 */}
      <Dialog open={!!temporaryPassword} onOpenChange={handleClosePasswordDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>密码重置成功</DialogTitle>
            <DialogDescription>
              用户「{resetPasswordUser?.username}」的临时密码已生成，请复制并妥善保管。
              用户首次登录后需要修改密码。
            </DialogDescription>
          </DialogHeader>
          <div className="flex items-center gap-2 p-4 bg-muted rounded-lg">
            <code className="flex-1 text-lg font-mono select-all">{temporaryPassword}</code>
            <Button
              variant="outline"
              size="icon"
              onClick={handleCopyPassword}
              title="复制密码"
            >
              {copied ? (
                <Check className="h-4 w-4 text-green-500" />
              ) : (
                <Copy className="h-4 w-4" />
              )}
            </Button>
          </div>
          <DialogFooter>
            <Button onClick={handleClosePasswordDialog}>
              关闭
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Create User Dialog */}
      <UserForm
        open={showCreateUser}
        onOpenChange={setShowCreateUser}
        onSuccess={() => refetch()}
      />

      {/* Set Password Dialog */}
      <SetPasswordDialog
        user={setPasswordUser}
        open={showSetPassword}
        onOpenChange={setShowSetPassword}
      />

      {/* Update Role Dialog */}
      <UpdateRoleDialog
        user={updateRoleUser}
        open={showUpdateRole}
        onOpenChange={setShowUpdateRole}
      />
    </div>
  );
}
