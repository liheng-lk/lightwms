import { NextResponse } from 'next/server';
import { getAuthCookies, setAuthCookies, clearAuthCookies } from '@/lib/auth/cookies';

const BACKEND_URL = process.env.BACKEND_URL || 'http://backend:8000';

// 安全 JSON 解析：避免非 JSON 响应导致崩溃
async function safeJsonParse(response: Response): Promise<any> {
  const text = await response.text();
  try {
    return JSON.parse(text);
  } catch {
    return { detail: text || 'Unknown error' };
  }
}

/**
 * Refresh 设计原则：
 * 1. 无全局锁（serverless/多实例下内存锁不可靠）
 * 2. 幂等可重复调用
 * 3. 失败即清 cookie 并返回 401
 * 
 * 并发去重在 proxy route 内处理（同一请求链），不在这里做全局锁
 */
export async function POST() {
  const { refreshToken } = await getAuthCookies();
  
  // 无 refresh token，直接清除并返回 401
  if (!refreshToken) {
    await clearAuthCookies();
    return NextResponse.json(
      { detail: 'No refresh token' },
      { status: 401 }
    );
  }
  
  try {
    const response = await fetch(`${BACKEND_URL}/api/v1/auth/refresh/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refresh: refreshToken }),
    });
    
    // refresh 失败（401/400），一次性清除并返回 401
    if (!response.ok) {
      await clearAuthCookies();
      return NextResponse.json(
        { detail: 'Refresh failed' },
        { status: 401 }
      );
    }
    
    const data = await safeJsonParse(response);
    await setAuthCookies(data.access, data.refresh);
    
    return NextResponse.json({ success: true });
  } catch (error) {
    // 网络错误也清除
    await clearAuthCookies();
    return NextResponse.json(
      { detail: 'Refresh failed' },
      { status: 401 }
    );
  }
}
