'use client';

import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
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
import { Copy, Check } from 'lucide-react';
import { useCreateInviteCode } from '@/lib/hooks/use-invite-codes';
import type { InviteCode, UserRole } from '@/lib/types';

interface InviteCodeFormProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSuccess?: () => void;
}

type DefaultRole = Exclude<UserRole, 'super_admin'>;

const roleOptions = [
  { value: 'read_only_user', label: '普通用户' },
  { value: 'item_manager', label: '物品管理员' },
] as const;

export function InviteCodeForm({ open, onOpenChange, onSuccess }: InviteCodeFormProps) {
  const [maxUses, setMaxUses] = useState('10');
  const [defaultRole, setDefaultRole] = useState<DefaultRole>('read_only_user' as DefaultRole);
  const [expiresAt, setExpiresAt] = useState('');
  const [createdCode, setCreatedCode] = useState<InviteCode | null>(null);
  const [copied, setCopied] = useState(false);

  const { mutate: createMutation, isPending } = useCreateInviteCode();

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    createMutation(
      {
        max_uses: parseInt(maxUses, 10),
        default_role: defaultRole,
        expires_at: expiresAt || null,
      },
      {
        onSuccess: (data) => {
          setCreatedCode(data);
          onSuccess?.();
        },
      }
    );
  };

  const handleCopyCode = async () => {
    if (!createdCode) return;
    const registerUrl = `${window.location.origin}/register?code=${createdCode.code}`;
    await navigator.clipboard.writeText(registerUrl);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleClose = () => {
    setMaxUses('10');
    setDefaultRole('read_only_user' as DefaultRole);
    setExpiresAt('');
    setCreatedCode(null);
    setCopied(false);
    onOpenChange(false);
  };

  if (createdCode) {
    return (
      <Dialog open={open} onOpenChange={handleClose}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>邀请码创建成功</DialogTitle>
            <DialogDescription>请复制邀请码或注册链接并只发送给指定人员。</DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div>
              <Label className="text-sm text-muted-foreground">邀请码</Label>
              <div className="flex items-center gap-2 mt-1 p-3 bg-muted rounded-lg">
                <code className="flex-1 text-lg font-mono">{createdCode.code}</code>
              </div>
            </div>
            <div>
              <Label className="text-sm text-muted-foreground">注册链接</Label>
              <div className="flex items-center gap-2 mt-1 p-3 bg-muted rounded-lg">
                <code className="flex-1 text-sm font-mono break-all">
                  {window.location.origin}/register?code={createdCode.code}
                </code>
                <Button variant="outline" size="icon" onClick={handleCopyCode} title="复制链接">
                  {copied ? <Check className="h-4 w-4 text-green-500" /> : <Copy className="h-4 w-4" />}
                </Button>
              </div>
            </div>
            <div className="grid grid-cols-2 gap-4 text-sm">
              <div>
                <span className="text-muted-foreground">默认角色：</span>
                <span className="ml-1">
                  {roleOptions.find((r) => r.value === createdCode.default_role)?.label || createdCode.default_role}
                </span>
              </div>
              <div>
                <span className="text-muted-foreground">最大使用次数：</span>
                <span className="ml-1">{createdCode.max_uses}</span>
              </div>
            </div>
          </div>
          <DialogFooter><Button onClick={handleClose}>关闭</Button></DialogFooter>
        </DialogContent>
      </Dialog>
    );
  }

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>新增邀请码</DialogTitle>
          <DialogDescription>
            默认注册为普通用户。只有确实负责库存管理的人员才应选择“物品管理员”。
          </DialogDescription>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="maxUses">最大使用次数</Label>
            <Input id="maxUses" type="number" min="1" max="1000" value={maxUses} onChange={(e) => setMaxUses(e.target.value)} required />
          </div>

          <div className="space-y-2">
            <Label htmlFor="defaultRole">注册后角色</Label>
            <Select value={defaultRole} onValueChange={(v) => setDefaultRole(v as DefaultRole)}>
              <SelectTrigger><SelectValue placeholder="选择默认角色" /></SelectTrigger>
              <SelectContent>
                {roleOptions.map((option) => (
                  <SelectItem key={option.value} value={option.value}>{option.label}</SelectItem>
                ))}
              </SelectContent>
            </Select>
            {defaultRole === ('item_manager' as DefaultRole) && (
              <p className="text-xs text-amber-600">
                物品管理员可修改自己负责的库存并代办业务，请仅用于可信任的仓管人员。
              </p>
            )}
          </div>

          <div className="space-y-2">
            <Label htmlFor="expiresAt">过期时间（可选）</Label>
            <Input id="expiresAt" type="datetime-local" value={expiresAt} onChange={(e) => setExpiresAt(e.target.value)} />
            <p className="text-xs text-muted-foreground">正式环境建议设置过期时间并限制使用次数。</p>
          </div>

          <DialogFooter>
            <Button type="button" variant="outline" onClick={handleClose}>取消</Button>
            <Button type="submit" disabled={isPending}>{isPending ? '创建中...' : '创建'}</Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
