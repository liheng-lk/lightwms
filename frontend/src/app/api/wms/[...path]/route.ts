import { NextRequest, NextResponse } from 'next/server';
import { getAuthCookies, setAuthCookies, clearAuthCookies } from '@/lib/auth/cookies';

const BACKEND_URL = process.env.BACKEND_URL || 'http://backend:8000';

// 需要过滤的 hop-by-hop headers + cookie（不转发给 Django）
const FILTERED_HEADERS = new Set([
  'connection',
  'keep-alive',
  'proxy-authenticate',
  'proxy-authorization',
  'te',
  'trailers',
  'transfer-encoding',
  'upgrade',
  'host',
  'cookie',  // 不转发 cookie 给 Django，用 Authorization header
]);

// 安全 JSON 解析：避免非 JSON 响应导致崩溃
async function safeJsonParse(response: Response): Promise<any> {
  const text = await response.text();
  try {
    return JSON.parse(text);
  } catch {
    return { detail: text || 'Unknown error' };
  }
}

async function proxyRequest(
  request: NextRequest,
  method: string
): Promise<NextResponse> {
  const { accessToken, refreshToken } = await getAuthCookies();
  
  // 检查是否已经重试过（防止无限刷新循环）
  const isRetried = request.headers.get('x-proxy-retried') === '1';
  
  // 构建后端 URL（确保末尾有斜杠，避免 Django 301 重定向）
  let path = request.nextUrl.pathname.replace('/api/wms', '/api/v1');
  // 确保路径末尾有斜杠（除非有查询参数或文件扩展名）
  if (!path.endsWith('/') && !path.includes('.')) {
    path = path + '/';
  }
  const url = new URL(path, BACKEND_URL);
  url.search = request.nextUrl.search;
  
  // 转发原始 headers（过滤 hop-by-hop 和 cookie）
  const headers = new Headers();
  request.headers.forEach((value, key) => {
    if (!FILTERED_HEADERS.has(key.toLowerCase())) {
      headers.set(key, value);
    }
  });
  
  // 添加 Authorization
  if (accessToken) {
    headers.set('Authorization', `Bearer ${accessToken}`);
  }
  
  // 准备请求体（GET/HEAD 不读 body）
  let body: ArrayBuffer | null = null;
  if (method !== 'GET' && method !== 'HEAD') {
    try {
      body = await request.arrayBuffer();
    } catch {}
  }
  
  // 发送请求（不自动跟随重定向，手动处理以保留 Authorization header）
  let response = await fetch(url.toString(), {
    method,
    headers,
    body: body && body.byteLength > 0 ? body : undefined,
    redirect: 'manual',
  });
  
  // 手动处理重定向，保留 Authorization header
  if (response.status === 301 || response.status === 302 || response.status === 307 || response.status === 308) {
    const redirectUrl = response.headers.get('location');
    if (redirectUrl) {
      const absoluteUrl = new URL(redirectUrl, url);
      response = await fetch(absoluteUrl.toString(), {
        method,
        headers,
        body: body && body.byteLength > 0 ? body : undefined,
        redirect: 'manual',
      });
    }
  }
  
  // 处理 401：尝试刷新 token 并重试一次（仅当未重试过）
  if (response.status === 401 && !isRetried && refreshToken) {
    try {
      // 直接调用后端刷新接口
      const refreshResponse = await fetch(`${BACKEND_URL}/api/v1/auth/refresh/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ refresh: refreshToken }),
      });
      
      if (refreshResponse.ok) {
        const tokens = await safeJsonParse(refreshResponse);
        await setAuthCookies(tokens.access, tokens.refresh);
        
        // 用新 token 重试
        headers.set('Authorization', `Bearer ${tokens.access}`);
        headers.set('x-proxy-retried', '1');
        
        response = await fetch(url.toString(), {
          method,
          headers,
          body: body && body.byteLength > 0 ? body : undefined,
          redirect: 'manual',
        });
        
        // 手动处理重定向
        if (response.status === 301 || response.status === 302 || response.status === 307 || response.status === 308) {
          const redirectUrl = response.headers.get('location');
          if (redirectUrl) {
            const absoluteUrl = new URL(redirectUrl, url);
            response = await fetch(absoluteUrl.toString(), {
              method,
              headers,
              body: body && body.byteLength > 0 ? body : undefined,
              redirect: 'manual',
            });
          }
        }
      } else {
        // 刷新失败，返回 401
        await clearAuthCookies();
        return NextResponse.json(
          { detail: 'Authentication required' },
          { status: 401 }
        );
      }
    } catch {
      await clearAuthCookies();
      return NextResponse.json(
        { detail: 'Authentication required' },
        { status: 401 }
      );
    }
  }
  
  // 根据 Content-Type 决定返回方式
  const contentType = response.headers.get('content-type') || '';
  
  // JSON 响应
  if (contentType.includes('application/json')) {
    const data = await safeJsonParse(response);
    return NextResponse.json(data, { status: response.status });
  }
  
  // 二进制/文件下载：直接 stream 返回
  const responseHeaders = new Headers();
  response.headers.forEach((value, key) => {
    if (!FILTERED_HEADERS.has(key.toLowerCase())) {
      responseHeaders.set(key, value);
    }
  });
  
  return new NextResponse(response.body, {
    status: response.status,
    headers: responseHeaders,
  });
}

export async function GET(request: NextRequest) {
  return proxyRequest(request, 'GET');
}

export async function POST(request: NextRequest) {
  return proxyRequest(request, 'POST');
}

export async function PATCH(request: NextRequest) {
  return proxyRequest(request, 'PATCH');
}

export async function PUT(request: NextRequest) {
  return proxyRequest(request, 'PUT');
}

export async function DELETE(request: NextRequest) {
  return proxyRequest(request, 'DELETE');
}
