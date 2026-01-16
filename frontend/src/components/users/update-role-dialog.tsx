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

const roleOptions: { value: UserRole; label: string }[] = [
  { value: 'super_admin', label: '超级管理员' },
  { value: 'item_manager', label: '物品管理员' },
];

export function UpdateRoleDialog({ user, open, onOpenChange }: UpdateRoleDialogProps) {
  const [selectedRole, setSelectedRole] = useState<UserRole>('item_manager');
  const { mutate: updateRole, isPending } = useUpdateUserRole();

  // 当用户变化时，更新选中的角色
  useEffect(() => {
    if (user) {
      setSelectedRole(user.role);
    }
  }, [user]);

  const handleSubmit = () => {
    if (!user) return;
    
    updateRole(
      {
        id: user.id,
        data: { role: selectedRole },
      },
      {
        onSuccess: () => {
          onOpenChange(false);
        },
      }
    );
  };

  const handleClose = () => {
    onOpenChange(false);
  };

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent className="sm:max-w-[425px]">
        <DialogHeader>
          <DialogTitle>修改用户角色</DialogTitle>
          <DialogDescription>
            修改用户「{user?.username}」的角色权限
          </DialogDescription>
        </DialogHeader>
        <div className="space-y-4 py-4">
          <div className="space-y-2">
            <Label htmlFor="role">角色</Label>
            <Select
              value={selectedRole}
              onValueChange={(value) => setSelectedRole(value as UserRole)}
              disabled={isPending}
            >
              <SelectTrigger>
                <SelectValue placeholder="选择角色" />
              </SelectTrigger>
              <SelectContent>
                {roleOptions.map((option) => (
                  <SelectItem key={option.value} value={option.value}>
                    {option.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          
          <div className="text-sm text-muted-foreground space-y-1">
            <p>角色权限说明：</p>
            <ul className="list-disc list-inside space-y-1 ml-2">
              <li><strong>超级管理员</strong>：拥有所有权限，可管理用户和系统设置</li>
              <li><strong>物品管理员</strong>：可管理物品、分类、仓库等</li>
              <li><strong>只读用户</strong>：只能查看数据，不能进行修改操作</li>
            </ul>
          </div>
        </div>
        <DialogFooter>
          <Button type="button" variant="outline" onClick={handleClose} disabled={isPending}>
            取消
          </Button>
          <Button 
            onClick={handleSubmit} 
            disabled={isPending || selectedRole === user?.role}
          >
            {isPending ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                保存中...
              </>
            ) : (
              '保存'
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
