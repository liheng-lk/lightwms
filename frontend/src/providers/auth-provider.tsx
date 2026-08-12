'use client';

import {
  createContext,
  useContext,
  useCallback,
  ReactNode,
} from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import type { User } from '@/lib/types';

interface AuthContextType {
  user: User | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  login: (username: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  refetchUser: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

async function safeJsonParse(response: Response): Promise<any> {
  const text = await response.text();
  try {
    return JSON.parse(text);
  } catch {
    return { detail: text || 'Unknown error' };
  }
}

async function fetchMe(): Promise<User | null> {
  const response = await fetch('/api/auth/me/');
  if (response.status === 401) return null;
  if (!response.ok) {
    const error = await safeJsonParse(response);
    throw new Error(error.detail || 'Failed to fetch user');
  }
  return safeJsonParse(response);
}

async function doLogin(username: string, password: string): Promise<void> {
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
  await fetch('/api/auth/logout/', { method: 'POST' });
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const queryClient = useQueryClient();
  const { data: user, isLoading, refetch } = useQuery({
    queryKey: ['auth', 'me'],
    queryFn: fetchMe,
    retry: false,
    staleTime: 5 * 60 * 1000,
    refetchOnWindowFocus: false,
    refetchOnReconnect: false,
  });

  const login = useCallback(async (username: string, password: string) => {
    await doLogin(username, password);
    await refetch();
  }, [refetch]);

  const logout = useCallback(async () => {
    await doLogout();
    queryClient.clear();
  }, [queryClient]);

  const refetchUser = useCallback(() => { void refetch(); }, [refetch]);

  return (
    <AuthContext.Provider value={{
      user: user ?? null,
      isLoading,
      isAuthenticated: !!user,
      login,
      logout,
      refetchUser,
    }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) throw new Error('useAuth must be used within AuthProvider');
  return context;
}
