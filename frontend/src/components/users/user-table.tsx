'use client';

import { Ban, KeyRound, Lock, CheckCircle, Shield } from 'lucide-react';
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
import { useDisableUser, useEnableUser } from '@/lib/hooks/use-users';
import { formatDate } from '@/lib/utils/date';
import type { User, UserRole } from '@/lib/types';

interface UserTableProps {
  users: User[];
  isLoading?: boolean;
  onResetPassword?: (user: User) => void;
  onSetPassword?: (user: User) => void;
  onUpdateRole?: (user: User) => void;
  onDisableSuccess?: () => void;
}

const roleLabels: Record<UserRole, string> = {
  super_admin: '超级管理员',
  item_manager: '物品管理员',
};

const roleVariants: Record<UserRole, 'default' | 'secondary' | 'outline'> = {
  super_admin: 'default',
  item_manager: 'secondary',
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

  const handleDisable = (id: number) => {
    disableUserMutation(id, {
      onSuccess: () => {
        onDisableSuccess?.();
      },
    });
  };

  const handleEnable = (id: number) => {
    enableUserMutation(id, {
      onSuccess: () => {
        onDisableSuccess?.();
      },
    });
  };

  if (isLoading) {
    return <UserTableSkeleton />;
  }
  
  if (users.length === 0) {
    return (
      <div className="text-center py-12 text-muted-foreground">
        暂无用户数据
      </div>
    );
  }
  
  return (
    <div className="border rounded-lg overflow-hidden">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>用户名</TableHead>
            <TableHead className="w-[120px]">角色</TableHead>
            <TableHead className="w-[80px]">状态</TableHead>
            <TableHead className="hidden md:table-cell">注册时间</TableHead>
            <TableHead className="w-[120px]">操作</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {users.map((user) => (
            <TableRow key={user.id}>
              <TableCell className="font-medium">
                {user.username}
              </TableCell>
              <TableCell>
                <Badge variant={roleVariants[user.role]}>
                  {roleLabels[user.role]}
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
                  {/* Update Role Button */}
                  <Button
                    variant="ghost"
                    size="icon"
                    onClick={() => onUpdateRole?.(user)}
                    title="修改角色"
                  >
                    <Shield className="h-4 w-4" />
                  </Button>
                  
                  {/* Set Password Button */}
                  <Button
                    variant="ghost"
                    size="icon"
                    onClick={() => onSetPassword?.(user)}
                    title="设置密码"
                  >
                    <Lock className="h-4 w-4" />
                  </Button>
                  
                  {/* Reset Password Button - Requirements 18.4 */}
                  <Button
                    variant="ghost"
                    size="icon"
                    onClick={() => onResetPassword?.(user)}
                    title="重置密码"
                  >
                    <KeyRound className="h-4 w-4" />
                  </Button>
                  
                  {/* Enable/Disable User Button - Requirements 18.3 */}
                  {user.is_active ? (
                    <AlertDialog>
                      <AlertDialogTrigger asChild>
                        <Button
                          variant="ghost"
                          size="icon"
                          title="禁用用户"
                          disabled={isDisabling}
                        >
                          <Ban className="h-4 w-4" />
                        </Button>
                      </AlertDialogTrigger>
                      <AlertDialogContent>
                        <AlertDialogHeader>
                          <AlertDialogTitle>确认禁用用户</AlertDialogTitle>
                          <AlertDialogDescription>
                            确定要禁用用户「{user.username}」吗？禁用后该用户将无法登录系统。
                          </AlertDialogDescription>
                        </AlertDialogHeader>
                        <AlertDialogFooter>
                          <AlertDialogCancel>取消</AlertDialogCancel>
                          <AlertDialogAction
                            onClick={() => handleDisable(user.id)}
                          >
                            确认禁用
                          </AlertDialogAction>
                        </AlertDialogFooter>
                      </AlertDialogContent>
                    </AlertDialog>
                  ) : (
                    <AlertDialog>
                      <AlertDialogTrigger asChild>
                        <Button
                          variant="ghost"
                          size="icon"
                          title="启用用户"
                          disabled={isEnabling}
                        >
                          <CheckCircle className="h-4 w-4 text-green-500" />
                        </Button>
                      </AlertDialogTrigger>
                      <AlertDialogContent>
                        <AlertDialogHeader>
                          <AlertDialogTitle>确认启用用户</AlertDialogTitle>
                          <AlertDialogDescription>
                            确定要启用用户「{user.username}」吗？启用后该用户可以正常登录系统。
                          </AlertDialogDescription>
                        </AlertDialogHeader>
                        <AlertDialogFooter>
                          <AlertDialogCancel>取消</AlertDialogCancel>
                          <AlertDialogAction
                            onClick={() => handleEnable(user.id)}
                          >
                            确认启用
                          </AlertDialogAction>
                        </AlertDialogFooter>
                      </AlertDialogContent>
                    </AlertDialog>
                  )}
                </div>
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
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
            <TableHead className="w-[120px]">操作</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {Array.from({ length: 5 }).map((_, i) => (
            <TableRow key={i}>
              <TableCell><Skeleton className="h-4 w-24" /></TableCell>
              <TableCell><Skeleton className="h-5 w-20" /></TableCell>
              <TableCell><Skeleton className="h-5 w-12" /></TableCell>
              <TableCell className="hidden md:table-cell"><Skeleton className="h-4 w-28" /></TableCell>
              <TableCell><Skeleton className="h-8 w-16" /></TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}
