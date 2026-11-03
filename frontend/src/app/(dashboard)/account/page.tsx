'use client';

import { useState } from 'react';
import { KeyRound, ShieldCheck, UserRound } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { ChangePasswordDialog } from '@/components/users/change-password-dialog';
import { useAuth } from '@/providers/auth-provider';

const roleLabels: Record<string, string> = {
  super_admin: '超级管理员',
  item_manager: '物品管理员',
  read_only_user: '普通用户',
};

export default function AccountPage() {
  const { user } = useAuth();
  const [showChangePassword, setShowChangePassword] = useState(false);

  if (!user) {
    return null;
  }

  return (
    <div className="space-y-6 max-w-3xl">
      <div>
        <h1 className="text-2xl font-bold">账户设置</h1>
        <p className="text-muted-foreground">管理当前登录账户和密码安全</p>
      </div>

      <div className="grid gap-6">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <UserRound className="h-5 w-5" />
              当前账户
            </CardTitle>
            <CardDescription>您只能修改自己的账户密码</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3 text-sm">
            <div className="flex items-center justify-between gap-4">
              <span className="text-muted-foreground">用户名</span>
              <span className="font-medium">{user.username}</span>
            </div>
            <div className="flex items-center justify-between gap-4">
              <span className="text-muted-foreground">账户角色</span>
              <span className="font-medium">{roleLabels[user.role] ?? user.role}</span>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <ShieldCheck className="h-5 w-5" />
              账户安全
            </CardTitle>
            <CardDescription>
              修改密码需要验证当前密码。修改成功后，已有登录令牌将失效，以保护账户安全。
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Button onClick={() => setShowChangePassword(true)}>
              <KeyRound className="h-4 w-4 mr-2" />
              修改我的密码
            </Button>
          </CardContent>
        </Card>
      </div>

      <ChangePasswordDialog
        open={showChangePassword}
        onOpenChange={setShowChangePassword}
      />
    </div>
  );
}
