'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { RotateCcw, Palette, Image, ImageIcon, KeyRound, RefreshCw, CircleCheck, ArrowUpCircle } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { ThemePicker } from '@/components/settings/theme-picker';
import { BackgroundPicker } from '@/components/settings/background-picker';
import { LogoPicker } from '@/components/settings/logo-picker';
import { ChangePasswordDialog } from '@/components/users/change-password-dialog';
import { useTheme } from '@/providers/theme-provider';
import { useAuth } from '@/providers/auth-provider';
import { useVersionInfo } from '@/lib/hooks/use-version';

export default function SettingsPage() {
  const { resetSettings } = useTheme();
  const { user } = useAuth();
  const router = useRouter();
  const [showChangePassword, setShowChangePassword] = useState(false);
  const { data: versionInfo, isFetching: isCheckingVersion, refetch: checkVersion } = useVersionInfo();

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
          <p className="text-muted-foreground">管理系统版本、账户安全与界面外观</p>
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
              {versionInfo?.update_available ? (
                <ArrowUpCircle className="h-5 w-5" />
              ) : (
                <CircleCheck className="h-5 w-5" />
              )}
              版本更新
            </CardTitle>
            <CardDescription>
              系统每 30 分钟自动检测已发布版本，也可以立即手动检查
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="flex flex-wrap items-center gap-3 text-sm">
              <span>当前版本：</span>
              <Badge variant="outline">
                {versionInfo?.current_version ? `v${versionInfo.current_version}` : '读取中...'}
              </Badge>
              {versionInfo?.latest_version && (
                <>
                  <span>最新版本：</span>
                  <Badge variant={versionInfo.update_available ? 'default' : 'secondary'}>
                    v{versionInfo.latest_version}
                  </Badge>
                </>
              )}
            </div>

            {versionInfo?.update_available ? (
              <p className="text-sm font-medium">
                检测到新版本 v{versionInfo.latest_version}，可按当前部署方式拉取新版镜像并升级。
              </p>
            ) : versionInfo?.latest_version ? (
              <p className="text-sm text-muted-foreground">当前已是最新版本。</p>
            ) : versionInfo?.error ? (
              <p className="text-sm text-muted-foreground">{versionInfo.error}</p>
            ) : null}

            <Button
              variant="outline"
              size="sm"
              onClick={() => checkVersion()}
              disabled={isCheckingVersion}
            >
              <RefreshCw className={`h-4 w-4 mr-2 ${isCheckingVersion ? 'animate-spin' : ''}`} />
              {isCheckingVersion ? '检查中...' : '立即检查更新'}
            </Button>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <KeyRound className="h-5 w-5" />
              账户安全
            </CardTitle>
            <CardDescription>
              管理您的账户密码
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Button variant="outline" onClick={() => setShowChangePassword(true)}>
              修改密码
            </Button>
          </CardContent>
        </Card>

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

      <ChangePasswordDialog
        open={showChangePassword}
        onOpenChange={setShowChangePassword}
      />
    </div>
  );
}
