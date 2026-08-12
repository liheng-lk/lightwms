'use client';

import { useState, useEffect } from 'react';
import { Loader2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
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
import { useUpdateUserRole } from '@/lib/hooks/use-users';
import type { User, UserRole } from '@/lib/types';

interface UpdateRoleDialogProps {
  user: User | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

const roleOptions = [
  { value: 'read_only_user', label: '普通用户' },
  { value: 'item_manager', label: '物品管理员' },
  { value: 'super_admin', label: '超级管理员' },
] as const;

export function UpdateRoleDialog({ user, open, onOpenChange }: UpdateRoleDialogProps) {
  const [selectedRole, setSelectedRole] = useState<UserRole>('read_only_user' as UserRole);
  const { mutate: updateRole, isPending } = useUpdateUserRole();

  useEffect(() => {
    if (user) setSelectedRole(user.role);
  }, [user]);

  const handleSubmit = () => {
    if (!user) return;
    updateRole(
      { id: user.id, data: { role: selectedRole } },
      { onSuccess: () => onOpenChange(false) }
    );
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[425px]">
        <DialogHeader>
          <DialogTitle>修改用户角色</DialogTitle>
          <DialogDescription>
            修改用户「{user?.username}」的角色。提升权限前请确认其实际职责。
          </DialogDescription>
        </DialogHeader>
        <div className="space-y-4 py-4">
          <div className="space-y-2">
            <Label htmlFor="role">角色</Label>
            <Select value={selectedRole} onValueChange={(value) => setSelectedRole(value as UserRole)} disabled={isPending}>
              <SelectTrigger><SelectValue placeholder="选择角色" /></SelectTrigger>
              <SelectContent>
                {roleOptions.map((option) => (
                  <SelectItem key={option.value} value={option.value}>{option.label}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div className="rounded-md border p-3 text-sm text-muted-foreground space-y-1">
            <p><strong className="text-foreground">普通用户</strong>：查看库存、查看自己的业务记录、归还自己的借用。</p>
            <p><strong className="text-foreground">物品管理员</strong>：管理自己负责的物品，并代办借用、领用和补货。</p>
            <p><strong className="text-foreground">超级管理员</strong>：管理全部库存、用户、邀请码和系统设置。</p>
          </div>
        </div>
        <DialogFooter>
          <Button type="button" variant="outline" onClick={() => onOpenChange(false)} disabled={isPending}>取消</Button>
          <Button onClick={handleSubmit} disabled={isPending || selectedRole === user?.role}>
            {isPending ? <><Loader2 className="mr-2 h-4 w-4 animate-spin" />保存中...</> : '保存'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
