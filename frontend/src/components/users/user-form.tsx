'use client';

import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { Loader2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { useCreateUser } from '@/lib/hooks/use-users';
import type { UserRole } from '@/lib/types';

const createUserSchema = z.object({
  username: z.string()
    .min(3, '用户名至少3个字符')
    .max(30, '用户名最多30个字符')
    .regex(/^[\w\u4e00-\u9fa5]+$/, '用户名只能包含字母、数字、下划线和中文'),
  password: z.string()
    .min(8, '密码至少8个字符')
    .max(128, '密码最多128个字符'),
  role: z.enum(['super_admin', 'item_manager', 'read_only_user'] as const),
  phone: z.string().optional(),
  department: z.string().optional(),
});

type CreateUserForm = z.infer<typeof createUserSchema>;

interface UserFormProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSuccess?: () => void;
}

const roleOptions = [
  { value: 'read_only_user', label: '普通用户' },
  { value: 'item_manager', label: '物品管理员' },
  { value: 'super_admin', label: '超级管理员' },
] as const;

export function UserForm({ open, onOpenChange, onSuccess }: UserFormProps) {
  const [selectedRole, setSelectedRole] = useState<UserRole>('read_only_user' as UserRole);
  const { mutate: createUser, isPending } = useCreateUser();

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<CreateUserForm>({
    resolver: zodResolver(createUserSchema),
    defaultValues: { role: 'read_only_user' },
  });

  const resetForm = () => {
    reset({ role: 'read_only_user' });
    setSelectedRole('read_only_user' as UserRole);
  };

  const onSubmit = (data: CreateUserForm) => {
    createUser(
      { ...data, role: selectedRole },
      {
        onSuccess: () => {
          resetForm();
          onOpenChange(false);
          onSuccess?.();
        },
      }
    );
  };

  const handleClose = () => {
    resetForm();
    onOpenChange(false);
  };

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent className="sm:max-w-[425px]">
        <DialogHeader>
          <DialogTitle>添加用户</DialogTitle>
          <DialogDescription>
            新账户默认使用最小权限的“普通用户”，需要库存管理权限时再单独提升。
          </DialogDescription>
        </DialogHeader>
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="username">用户名 *</Label>
            <Input id="username" placeholder="请输入用户名" disabled={isPending} {...register('username')} />
            {errors.username && <p className="text-sm text-destructive">{errors.username.message}</p>}
          </div>

          <div className="space-y-2">
            <Label htmlFor="password">密码 *</Label>
            <Input id="password" type="password" placeholder="至少 8 位，建议包含字母和数字" disabled={isPending} {...register('password')} />
            {errors.password && <p className="text-sm text-destructive">{errors.password.message}</p>}
          </div>

          <div className="space-y-2">
            <Label htmlFor="role">角色 *</Label>
            <Select value={selectedRole} onValueChange={(value) => setSelectedRole(value as UserRole)} disabled={isPending}>
              <SelectTrigger><SelectValue placeholder="选择角色" /></SelectTrigger>
              <SelectContent>
                {roleOptions.map((option) => (
                  <SelectItem key={option.value} value={option.value}>{option.label}</SelectItem>
                ))}
              </SelectContent>
            </Select>
            <p className="text-xs text-muted-foreground">
              普通用户仅查看库存及处理自己的借用；物品管理员负责自己名下物品；超级管理员拥有系统级权限。
            </p>
          </div>

          <div className="space-y-2">
            <Label htmlFor="phone">手机号（可选）</Label>
            <Input id="phone" type="tel" placeholder="请输入手机号" disabled={isPending} {...register('phone')} />
          </div>

          <div className="space-y-2">
            <Label htmlFor="department">部门（可选）</Label>
            <Input id="department" placeholder="请输入部门" disabled={isPending} {...register('department')} />
          </div>

          <DialogFooter>
            <Button type="button" variant="outline" onClick={handleClose} disabled={isPending}>取消</Button>
            <Button type="submit" disabled={isPending}>
              {isPending ? <><Loader2 className="mr-2 h-4 w-4 animate-spin" />创建中...</> : '创建用户'}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
