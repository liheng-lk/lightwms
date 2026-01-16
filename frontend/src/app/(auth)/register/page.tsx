'use client';

import { useState, Suspense } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import Link from 'next/link';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { Loader2, LayoutDashboard, Ticket } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
  CardFooter,
} from '@/components/ui/card';
import { useTheme } from '@/providers/theme-provider';
import { toast } from 'sonner';

const registerSchema = z.object({
  username: z.string()
    .min(3, '用户名至少3个字符')
    .max(30, '用户名最多30个字符')
    .regex(/^[a-zA-Z0-9_]+$/, '用户名只能包含字母、数字和下划线'),
  password: z.string()
    .min(6, '密码至少6个字符')
    .max(50, '密码最多50个字符'),
  confirmPassword: z.string(),
  phone: z.string().optional(),
  department: z.string().optional(),
}).refine((data) => data.password === data.confirmPassword, {
  message: '两次输入的密码不一致',
  path: ['confirmPassword'],
});

type RegisterForm = z.infer<typeof registerSchema>;

function RegisterForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { settings } = useTheme();
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  
  // 从 URL 获取邀请码，或使用手动输入的邀请码
  const urlInviteCode = searchParams.get('code') || '';
  const [manualInviteCode, setManualInviteCode] = useState('');
  const [showManualInput, setShowManualInput] = useState(!urlInviteCode);
  
  // 使用 URL 中的邀请码或手动输入的邀请码
  const inviteCode = urlInviteCode || manualInviteCode;
  
  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<RegisterForm>({
    resolver: zodResolver(registerSchema),
  });
  
  const onSubmit = async (data: RegisterForm) => {
    if (!inviteCode.trim()) {
      setError('请输入邀请码');
      return;
    }
    
    setError(null);
    setIsLoading(true);
    
    try {
      const response = await fetch('/api/wms/auth/register/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          username: data.username,
          password: data.password,
          invite_code: inviteCode.trim(),
          phone: data.phone || undefined,
          department: data.department || undefined,
        }),
      });
      
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || errorData.message || '注册失败');
      }
      
      toast.success('注册成功，请登录');
      router.push('/login');
    } catch (err) {
      if (err instanceof Error) {
        if (err.message.includes('invite') || err.message.includes('code')) {
          setError('邀请码无效或已过期');
        } else if (err.message.includes('username') || err.message.includes('exists')) {
          setError('用户名已存在');
        } else {
          setError(err.message || '注册失败，请重试');
        }
      } else {
        setError('注册失败，请重试');
      }
    } finally {
      setIsLoading(false);
    }
  };

  // 处理手动输入邀请码后继续注册
  const handleContinueWithCode = () => {
    if (manualInviteCode.trim()) {
      setShowManualInput(false);
      setError(null);
    } else {
      setError('请输入邀请码');
    }
  };

  // 显示邀请码输入界面
  if (showManualInput && !urlInviteCode) {
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
          <CardTitle className="text-2xl">注册</CardTitle>
          <CardDescription>请输入邀请码</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {error && (
              <div className="p-3 text-sm text-destructive bg-destructive/10 rounded-md">
                {error}
              </div>
            )}
            
            <div className="text-center text-muted-foreground text-sm mb-4">
              <p>请输入管理员提供的邀请码进行注册</p>
            </div>
            
            <div className="space-y-2">
              <Label htmlFor="inviteCode">邀请码</Label>
              <div className="relative">
                <Ticket className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                <Input
                  id="inviteCode"
                  type="text"
                  placeholder="请输入邀请码"
                  className="pl-10"
                  value={manualInviteCode}
                  onChange={(e) => setManualInviteCode(e.target.value.toUpperCase())}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') {
                      e.preventDefault();
                      handleContinueWithCode();
                    }
                  }}
                />
              </div>
            </div>
            
            <Button 
              type="button" 
              className="w-full" 
              onClick={handleContinueWithCode}
            >
              继续注册
            </Button>
          </div>
        </CardContent>
        <CardFooter className="justify-center">
          <Link href="/login" className="text-sm text-primary hover:underline">
            已有账户？去登录
          </Link>
        </CardFooter>
      </Card>
    );
  }
  
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
        <CardDescription>创建新账户</CardDescription>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          {error && (
            <div className="p-3 text-sm text-destructive bg-destructive/10 rounded-md">
              {error}
            </div>
          )}
          
          {/* 显示当前邀请码 */}
          <div className="space-y-2">
            <Label htmlFor="currentInviteCode">邀请码</Label>
            <div className="flex gap-2">
              <div className="relative flex-1">
                <Ticket className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                <Input
                  id="currentInviteCode"
                  type="text"
                  value={inviteCode}
                  className="pl-10 bg-muted"
                  readOnly
                  disabled={isLoading}
                />
              </div>
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={() => {
                  setManualInviteCode(inviteCode);
                  setShowManualInput(true);
                }}
                disabled={isLoading}
              >
                修改
              </Button>
            </div>
          </div>
          
          <div className="space-y-2">
            <Label htmlFor="username">用户名 *</Label>
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
            <Label htmlFor="password">密码 *</Label>
            <Input
              id="password"
              type="password"
              placeholder="请输入密码"
              autoComplete="new-password"
              disabled={isLoading}
              {...register('password')}
            />
            {errors.password && (
              <p className="text-sm text-destructive">{errors.password.message}</p>
            )}
          </div>
          
          <div className="space-y-2">
            <Label htmlFor="confirmPassword">确认密码 *</Label>
            <Input
              id="confirmPassword"
              type="password"
              placeholder="请再次输入密码"
              autoComplete="new-password"
              disabled={isLoading}
              {...register('confirmPassword')}
            />
            {errors.confirmPassword && (
              <p className="text-sm text-destructive">{errors.confirmPassword.message}</p>
            )}
          </div>
          
          <div className="space-y-2">
            <Label htmlFor="phone">手机号（可选）</Label>
            <Input
              id="phone"
              type="tel"
              placeholder="请输入手机号"
              disabled={isLoading}
              {...register('phone')}
            />
          </div>
          
          <div className="space-y-2">
            <Label htmlFor="department">部门（可选）</Label>
            <Input
              id="department"
              type="text"
              placeholder="请输入部门"
              disabled={isLoading}
              {...register('department')}
            />
          </div>
          
          <Button type="submit" className="w-full" disabled={isLoading}>
            {isLoading ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                注册中...
              </>
            ) : (
              '注册'
            )}
          </Button>
        </form>
      </CardContent>
      <CardFooter className="justify-center">
        <Link href="/login" className="text-sm text-primary hover:underline">
          已有账户？去登录
        </Link>
      </CardFooter>
    </Card>
  );
}

export default function RegisterPage() {
  return (
    <Suspense fallback={
      <Card>
        <CardHeader className="text-center">
          <CardTitle className="text-2xl">注册</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-center py-8">
            <Loader2 className="h-6 w-6 animate-spin" />
          </div>
        </CardContent>
      </Card>
    }>
      <RegisterForm />
    </Suspense>
  );
}
