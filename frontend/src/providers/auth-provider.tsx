'use client';

import {
  createContext,
  useContext,
  useCallback,
  ReactNode,
} from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';

interface User {
  id: number;
  username: string;
  email: string | null;
  phone: string | null;
  department: string;
  role: 'super_admin' | 'item_manager';
  is_active: boolean;
}

interface AuthContextType {
  user: User | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  login: (username: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  refetchUser: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

// 安全 JSON 解析：避免非 JSON 响应导致崩溃
async function safeJsonParse(response: Response): Promise<any> {
  const text = await response.text();
  try {
    return JSON.parse(text);
  } catch {
    return { detail: text || 'Unknown error' };
  }
}

// fetchMe: 401 返回 null（正常"未登录"状态），不 throw
async function fetchMe(): Promise<User | null> {
  // 注意：API 路径必须带尾部斜杠，与 Next.js trailingSlash 配置一致
  const response = await fetch('/api/auth/me/');
  
  // 401 是正常的"未登录"状态，返回 null 而不是 throw
  if (response.status === 401) {
    return null;
  }
  
  if (!response.ok) {
    // 其他错误才 throw
    const error = await safeJsonParse(response);
    throw new Error(error.detail || 'Failed to fetch user');
  }
  
  return safeJsonParse(response);
}

async function doLogin(username: string, password: string): Promise<void> {
  // 注意：API 路径必须带尾部斜杠，与 Next.js trailingSlash 配置一致
  const response = await fetch('/api/auth/login/', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username, password }),
  });
  
  if (!response.ok) {
    const error = await safeJsonParse(response);
    throw new Error(error.detail || 'Login failed');
  }
}

async function doLogout(): Promise<void> {
  // 注意：API 路径必须带尾部斜杠，与 Next.js trailingSlash 配置一致
  await fetch('/api/auth/logout/', { method: 'POST' });
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const queryClient = useQueryClient();
  
  const {
    data: user,
    isLoading,
    refetch,
  } = useQuery({
    queryKey: ['auth', 'me'],
    queryFn: fetchMe,
    retry: false,
    staleTime: 5 * 60 * 1000, // 5 分钟
    refetchOnWindowFocus: false, // 防止窗口聚焦时重新请求
    refetchOnReconnect: false, // 防止重连时重新请求
  });
  
  const login = useCallback(async (username: string, password: string) => {
    await doLogin(username, password);
    await refetch();
  }, [refetch]);
  
  const logout = useCallback(async () => {
    await doLogout();
    queryClient.clear(); // 清除所有缓存
  }, [queryClient]);
  
  const refetchUser = useCallback(() => {
    refetch();
  }, [refetch]);
  
  return (
    <AuthContext.Provider
      value={{
        user: user ?? null,
        isLoading,
        isAuthenticated: !!user,
        login,
        logout,
        refetchUser,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within AuthProvider');
  }
  return context;
}
