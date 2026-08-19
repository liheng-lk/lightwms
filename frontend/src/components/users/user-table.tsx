'use client';

import { useState } from 'react';
import { Ban, KeyRound, Lock, CheckCircle, Shield, Trash2 } from 'lucide-react';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import { Badge } from '@/components/ui/badge';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from '@/components/ui/alert-dialog';
import { useDeleteUser, useDisableUser, useEnableUser } from '@/lib/hooks/use-users';
import { formatDate } from '@/lib/utils/date';
import type { User } from '@/lib/types';

interface UserTableProps {
  users: User[];
  isLoading?: boolean;
  onResetPassword?: (user: User) => void;
  onSetPassword?: (user: User) => void;
  onUpdateRole?: (user: User) => void;
  onDisableSuccess?: () => void;
}

const roleLabels: Record<string, string> = {
  super_admin: '超级管理员',
  item_manager: '物品管理员',
  read_only_user: '普通用户',
};

const roleVariants: Record<string, 'default' | 'secondary' | 'outline'> = {
  super_admin: 'default',
  item_manager: 'secondary',
  read_only_user: 'outline',
};

export function UserTable({
  users,
  isLoading,
  onResetPassword,
  onSetPassword,
  onUpdateRole,
  onDisableSuccess,
}: UserTableProps) {
  const { mutate: disableUserMutation, isPending: isDisabling } = useDisableUser();
  const { mutate: enableUserMutation, isPending: isEnabling } = useEnableUser();
  const { mutate: deleteUserMutation, isPending: isDeleting } = useDeleteUser();
  const [deleteUser, setDeleteUser] = useState<User | null>(null);
  const [deleteError, setDeleteError] = useState<string | null>(null);

  const handleDisable = (id: number) => {
    disableUserMutation(id, { onSuccess: () => onDisableSuccess?.() });
  };

  const handleEnable = (id: number) => {
    enableUserMutation(id, { onSuccess: () => onDisableSuccess?.() });
  };

  const openDeleteDialog = (user: User) => {
    setDeleteError(null);
    setDeleteUser(user);
  };

  const handleDelete = () => {
    if (!deleteUser) return;
    setDeleteError(null);
    deleteUserMutation(deleteUser.id, {
      onSuccess: () => {
        setDeleteUser(null);
        onDisableSuccess?.();
      },
      onError: (error) => setDeleteError(error.message),
    });
  };

  if (isLoading) return <UserTableSkeleton />;

  if (users.length === 0) {
    return <div className="text-center py-12 text-muted-foreground">暂无用户数据</div>;
  }

  return (
    <>
      <div className="border rounded-lg overflow-hidden">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>用户名</TableHead>
              <TableHead className="w-[120px]">角色</TableHead>
              <TableHead className="w-[80px]">状态</TableHead>
              <TableHead className="hidden md:table-cell">注册时间</TableHead>
              <TableHead className="w-[220px]">操作</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {users.map((user) => (
              <TableRow key={user.id}>
                <TableCell className="font-medium">{user.username}</TableCell>
                <TableCell>
                  <Badge variant={roleVariants[user.role] || 'outline'}>
                    {roleLabels[user.role] || user.role}
                  </Badge>
                </TableCell>
                <TableCell>
                  <Badge variant={user.is_active ? 'default' : 'secondary'}>
                    {user.is_active ? '启用' : '禁用'}
                  </Badge>
                </TableCell>
                <TableCell className="hidden md:table-cell text-muted-foreground">
                  {user.created_at ? formatDate(user.created_at) : '-'}
                </TableCell>
                <TableCell>
                  <div className="flex items-center gap-1">
                    <Button variant="ghost" size="icon" onClick={() => onUpdateRole?.(user)} title="修改角色">
                      <Shield className="h-4 w-4" />
                    </Button>
                    <Button variant="ghost" size="icon" onClick={() => onSetPassword?.(user)} title="设置密码">
                      <Lock className="h-4 w-4" />
                    </Button>
                    <Button variant="ghost" size="icon" onClick={() => onResetPassword?.(user)} title="重置密码">
                      <KeyRound className="h-4 w-4" />
                    </Button>
                    {user.is_active ? (
                      <AlertDialog>
                        <AlertDialogTrigger asChild>
                          <Button variant="ghost" size="icon" title="禁用用户" disabled={isDisabling}>
                            <Ban className="h-4 w-4" />
                          </Button>
                        </AlertDialogTrigger>
                        <AlertDialogContent>
                          <AlertDialogHeader>
                            <AlertDialogTitle>确认禁用用户</AlertDialogTitle>
                            <AlertDialogDescription>
                              确定要禁用用户「{user.username}」吗？禁用后该用户将无法登录，现有令牌也应失效。
                            </AlertDialogDescription>
                          </AlertDialogHeader>
                          <AlertDialogFooter>
                            <AlertDialogCancel>取消</AlertDialogCancel>
                            <AlertDialogAction onClick={() => handleDisable(user.id)}>确认禁用</AlertDialogAction>
                          </AlertDialogFooter>
                        </AlertDialogContent>
                      </AlertDialog>
                    ) : (
                      <AlertDialog>
                        <AlertDialogTrigger asChild>
                          <Button variant="ghost" size="icon" title="启用用户" disabled={isEnabling}>
                            <CheckCircle className="h-4 w-4" />
                          </Button>
                        </AlertDialogTrigger>
                        <AlertDialogContent>
                          <AlertDialogHeader>
                            <AlertDialogTitle>确认启用用户</AlertDialogTitle>
                            <AlertDialogDescription>
                              确定要启用用户「{user.username}」吗？启用后该用户可以重新登录系统。
                            </AlertDialogDescription>
                          </AlertDialogHeader>
                          <AlertDialogFooter>
                            <AlertDialogCancel>取消</AlertDialogCancel>
                            <AlertDialogAction onClick={() => handleEnable(user.id)}>确认启用</AlertDialogAction>
                          </AlertDialogFooter>
                        </AlertDialogContent>
                      </AlertDialog>
                    )}
                    <Button
                      variant="ghost"
                      size="icon"
                      title="删除用户"
                      onClick={() => openDeleteDialog(user)}
                      disabled={isDeleting}
                    >
                      <Trash2 className="h-4 w-4 text-destructive" />
                    </Button>
                  </div>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>

      <AlertDialog
        open={!!deleteUser}
        onOpenChange={(open) => {
          if (!open && !isDeleting) {
            setDeleteUser(null);
            setDeleteError(null);
          }
        }}
      >
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>确认删除用户</AlertDialogTitle>
            <AlertDialogDescription>
              删除后用户「{deleteUser?.username}」将立即无法登录并从用户管理列表移除。
              若账号没有业务历史，系统会永久删除；若关联物品、库位、借用、领用、补货或发票等历史记录，系统会保留历史台账并归档账号。此操作不可撤销。
            </AlertDialogDescription>
          </AlertDialogHeader>
          {deleteError && (
            <div className="rounded-md border border-destructive/40 bg-destructive/10 p-3 text-sm text-destructive">
              {deleteError}
            </div>
          )}
          <AlertDialogFooter>
            <AlertDialogCancel disabled={isDeleting}>取消</AlertDialogCancel>
            <AlertDialogAction
              onClick={(event) => {
                event.preventDefault();
                handleDelete();
              }}
              disabled={isDeleting}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              {isDeleting ? '删除中...' : '确认删除'}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </>
  );
}

function UserTableSkeleton() {
  return (
    <div className="border rounded-lg overflow-hidden">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>用户名</TableHead>
            <TableHead className="w-[120px]">角色</TableHead>
            <TableHead className="w-[80px]">状态</TableHead>
            <TableHead className="hidden md:table-cell">注册时间</TableHead>
            <TableHead className="w-[220px]">操作</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {Array.from({ length: 5 }).map((_, i) => (
            <TableRow key={i}>
              <TableCell><Skeleton className="h-4 w-24" /></TableCell>
              <TableCell><Skeleton className="h-5 w-20" /></TableCell>
              <TableCell><Skeleton className="h-5 w-12" /></TableCell>
              <TableCell className="hidden md:table-cell"><Skeleton className="h-4 w-28" /></TableCell>
              <TableCell><Skeleton className="h-8 w-28" /></TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}
