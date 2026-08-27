'use client';

import { RotateCcw, Palette, Image, ImageIcon } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { ThemePicker } from '@/components/settings/theme-picker';
import { BackgroundPicker } from '@/components/settings/background-picker';
import { LogoPicker } from '@/components/settings/logo-picker';
import { useTheme } from '@/providers/theme-provider';
import { useAuth } from '@/providers/auth-provider';
import { useRouter } from 'next/navigation';
import { useEffect } from 'react';

export default function SettingsPage() {
  const { resetSettings } = useTheme();
  const { user } = useAuth();
  const router = useRouter();
  
  // 系统级配置仅 Super Admin 可访问。个人密码修改位于 /account，
  // 对所有已登录角色开放，避免把个人账户权限和系统管理权限混在一起。
  useEffect(() => {
    if (user && user.role !== 'super_admin') {
      router.push('/items');
    }
  }, [user, router]);
  
  if (!user || user.role !== 'super_admin') {
    return null;
  }
  
  return (
    <div className="space-y-6 max-w-4xl">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">系统设置</h1>
          <p className="text-muted-foreground">自定义系统级界面外观</p>
        </div>
        <Button variant="outline" onClick={resetSettings}>
          <RotateCcw className="h-4 w-4 mr-2" />
          恢复默认
        </Button>
      </div>
      
      <div className="grid gap-6">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Palette className="h-5 w-5" />
              主题设置
            </CardTitle>
            <CardDescription>
              选择系统界面的颜色主题
            </CardDescription>
          </CardHeader>
          <CardContent>
            <ThemePicker />
          </CardContent>
        </Card>
        
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Image className="h-5 w-5" />
              背景设置
            </CardTitle>
            <CardDescription>
              自定义系统背景颜色或图片
            </CardDescription>
          </CardHeader>
          <CardContent>
            <BackgroundPicker />
          </CardContent>
        </Card>
        
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <ImageIcon className="h-5 w-5" />
              Logo 设置
            </CardTitle>
            <CardDescription>
              自定义系统 Logo，将显示在侧边栏和登录页
            </CardDescription>
          </CardHeader>
          <CardContent>
            <LogoPicker />
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
