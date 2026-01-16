'use client';

import { useState, Suspense } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import Link from 'next/link';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { Loader2, LayoutDashboard } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import { useAuth } from '@/providers/auth-provider';
import { useTheme } from '@/providers/theme-provider';

const loginSchema = z.object({
  username: z.string().min(1, '请输入用户名'),
  password: z.string().min(1, '请输入密码'),
});

type LoginForm = z.infer<typeof loginSchema>;

function LoginForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { login } = useAuth();
  const { settings } = useTheme();
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  
  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<LoginForm>({
    resolver: zodResolver(loginSchema),
  });
  
  const onSubmit = async (data: LoginForm) => {
    setError(null);
    setIsLoading(true);
    
    try {
      await login(data.username, data.password);
      
      // 登录成功，使用硬跳转确保 cookie 被正确发送到服务端
      // router.push 是客户端路由，不会触发完整页面刷新，middleware 可能无法识别新的登录状态
      let next = searchParams.get('next') || '/items';
      // 确保路径以 / 结尾（trailingSlash: true 配置）
      if (!next.endsWith('/') && !next.includes('?')) {
        next = next + '/';
      }
      window.location.href = next;
    } catch (err) {
      if (err instanceof Error) {
        // 处理不同错误类型
        if (err.message.includes('credentials') || err.message.includes('password')) {
          setError('用户名或密码错误');
        } else if (err.message.includes('rate') || err.message.includes('limit')) {
          setError('登录尝试过于频繁，请稍后再试');
        } else if (err.message.includes('inactive') || err.message.includes('disabled')) {
          setError('账户已被禁用');
        } else {
          setError(err.message || '登录失败，请重试');
        }
      } else {
        setError('登录失败，请重试');
      }
    } finally {
      setIsLoading(false);
    }
  };
  
  return (
    <Card>
      <CardHeader className="text-center">
        <div className="flex justify-center mb-2">
          {settings.customLogo ? (
            <img
              src={settings.customLogo}
              alt="Logo"
              className="h-12 w-auto max-w-[200px] object-contain"
            />
          ) : (
            <div className="flex items-center gap-2">
              <LayoutDashboard className="h-8 w-8" />
              <CardTitle className="text-2xl">LightWMS</CardTitle>
            </div>
          )}
        </div>
        {!settings.customLogo && (
          <CardDescription>轻量级仓库管理系统</CardDescription>
        )}
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          {error && (
            <div className="p-3 text-sm text-destructive bg-destructive/10 rounded-md">
              {error}
            </div>
          )}
          
          <div className="space-y-2">
            <Label htmlFor="username">用户名</Label>
            <Input
              id="username"
              type="text"
              placeholder="请输入用户名"
              autoComplete="username"
              disabled={isLoading}
              {...register('username')}
            />
            {errors.username && (
              <p className="text-sm text-destructive">{errors.username.message}</p>
            )}
          </div>
          
          <div className="space-y-2">
            <Label htmlFor="password">密码</Label>
            <Input
              id="password"
              type="password"
              placeholder="请输入密码"
              autoComplete="current-password"
              disabled={isLoading}
              {...register('password')}
            />
            {errors.password && (
              <p className="text-sm text-destructive">{errors.password.message}</p>
            )}
          </div>
          
          <Button type="submit" className="w-full" disabled={isLoading}>
            {isLoading ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                登录中...
              </>
            ) : (
              '登录'
            )}
          </Button>
          
          <div className="text-center text-sm text-muted-foreground">
            还没有账号？{' '}
            <Link href="/register" className="text-primary hover:underline">
              立即注册
            </Link>
          </div>
        </form>
      </CardContent>
    </Card>
  );
}

export default function LoginPage() {
  return (
    <Suspense fallback={
      <Card>
        <CardHeader className="text-center">
          <CardTitle className="text-2xl">LightWMS</CardTitle>
          <CardDescription>轻量级仓库管理系统</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-center py-8">
            <Loader2 className="h-6 w-6 animate-spin" />
          </div>
        </CardContent>
      </Card>
    }>
      <LoginForm />
    </Suspense>
  );
}
