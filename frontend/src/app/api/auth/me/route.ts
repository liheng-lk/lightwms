import { NextRequest, NextResponse } from 'next/server';
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

export async function GET(request: NextRequest) {
  const { accessToken, refreshToken } = await getAuthCookies();
  
  // 无 token，返回 401
  if (!accessToken && !refreshToken) {
    return NextResponse.json({ detail: 'Not authenticated' }, { status: 401 });
  }
  
  // 尝试用 access token 获取用户信息
  if (accessToken) {
    const response = await fetch(`${BACKEND_URL}/api/v1/users/me/`, {
      headers: { Authorization: `Bearer ${accessToken}` },
    });
    
    if (response.ok) {
      const data = await safeJsonParse(response);
      return NextResponse.json(data);
    }
    
    // access token 无效但有 refresh token，尝试刷新
    if (response.status === 401 && refreshToken) {
      return await refreshAndRetry(refreshToken);
    }
    
    // 其他错误直接返回
    const error = await safeJsonParse(response);
    return NextResponse.json(error, { status: response.status });
  }
  
  // 只有 refresh token，尝试刷新后获取
  if (refreshToken) {
    return await refreshAndRetry(refreshToken);
  }
  
  return NextResponse.json({ detail: 'Not authenticated' }, { status: 401 });
}

async function refreshAndRetry(refreshToken: string): Promise<NextResponse> {
  try {
    // 直接调用后端刷新接口
    const refreshResponse = await fetch(`${BACKEND_URL}/api/v1/auth/refresh/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refresh: refreshToken }),
    });
    
    if (!refreshResponse.ok) {
      await clearAuthCookies();
      return NextResponse.json({ detail: 'Not authenticated' }, { status: 401 });
    }
    
    const tokens = await safeJsonParse(refreshResponse);
    await setAuthCookies(tokens.access, tokens.refresh);
    
    // 用新 token 获取用户信息
    const response = await fetch(`${BACKEND_URL}/api/v1/users/me/`, {
      headers: { Authorization: `Bearer ${tokens.access}` },
    });
    
    if (response.ok) {
      const data = await safeJsonParse(response);
      return NextResponse.json(data);
    }
    
    await clearAuthCookies();
    return NextResponse.json({ detail: 'Not authenticated' }, { status: 401 });
  } catch (error) {
    await clearAuthCookies();
    return NextResponse.json({ detail: 'Not authenticated' }, { status: 401 });
  }
}
