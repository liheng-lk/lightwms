import { NextRequest, NextResponse } from 'next/server';
import { setAuthCookies } from '@/lib/auth/cookies';

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

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    
    const response = await fetch(`${BACKEND_URL}/api/v1/auth/login/`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        // 让登录日志记录真实的浏览器 UA，而不是 Node fetch 的 UA
        'User-Agent': request.headers.get('user-agent') || '',
      },
      body: JSON.stringify(body),
    });
    
    if (!response.ok) {
      const error = await safeJsonParse(response);
      return NextResponse.json(error, { status: response.status });
    }
    
    const data = await safeJsonParse(response);
    await setAuthCookies(data.access, data.refresh);
    
    return NextResponse.json({ success: true });
  } catch (error) {
    return NextResponse.json(
      { detail: 'Internal server error' },
      { status: 500 }
    );
  }
}
