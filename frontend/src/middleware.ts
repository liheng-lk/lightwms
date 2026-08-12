import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

// 公开路径（无需登录）
const publicPaths = ['/login', '/register'];

// API 路径（不拦截）
const apiPaths = ['/api/'];

function firstForwardedValue(value: string | null): string | null {
  if (!value) return null;
  return value.split(',')[0]?.trim() || null;
}

/**
 * 反向代理后的浏览器地址必须使用“外部域名”，不能把容器内部的
 * :3000（Next.js）或 :8000（Django）泄露到 302 Location 中。
 *
 * 规则：
 * - 优先使用 X-Forwarded-Host / X-Forwarded-Proto；
 * - 代理场景下不再根据 X-Forwarded-Port 主动拼端口；
 * - 如果代理错误地把内部 3000/8000 塞进 Host，则主动移除；
 * - 本地直接访问 localhost:3000 时仍保留 3000，方便开发。
 */
function buildRedirectUrl(
  request: NextRequest,
  pathname: string,
  searchParams?: URLSearchParams
): URL {
  const forwardedHost = firstForwardedValue(request.headers.get('x-forwarded-host'));
  const forwardedProto = firstForwardedValue(request.headers.get('x-forwarded-proto'));
  const forwardedPort = firstForwardedValue(request.headers.get('x-forwarded-port'));
  const isCloudflare = request.headers.get('cf-connecting-ip') !== null;
  const isProxied = Boolean(forwardedHost || forwardedProto || forwardedPort || isCloudflare);

  const hostHeader = request.headers.get('host') || 'localhost';
  let host = forwardedHost || hostHeader;
  const protocol = (
    forwardedProto ||
    (isCloudflare ? 'https' : request.nextUrl.protocol.replace(':', '') || 'http')
  ).toLowerCase();

  // 仅在“确定经过代理”时清理内部服务端口，避免影响本地 localhost:3000 开发。
  if (isProxied && !host.startsWith('[')) {
    const match = host.match(/^(.*):(\d+)$/);
    if (match) {
      const [, hostname, port] = match;
      const isInternalPort = port === '3000' || port === '8000';
      const isDefaultPort =
        (protocol === 'https' && port === '443') ||
        (protocol === 'http' && port === '80');

      if (isInternalPort || isDefaultPort) {
        host = hostname;
      }
    }
  }

  const url = new URL(`${protocol}://${host}${pathname}`);
  if (searchParams) {
    searchParams.forEach((value, key) => {
      url.searchParams.set(key, value);
    });
  }
  return url;
}

export function middleware(request: NextRequest) {
  const { pathname, search } = request.nextUrl;

  // API 请求不拦截
  if (apiPaths.some((path) => pathname.startsWith(path))) {
    return NextResponse.next();
  }

  // 静态资源不拦截
  if (
    pathname.startsWith('/_next') ||
    pathname.startsWith('/favicon') ||
    pathname.includes('.')
  ) {
    return NextResponse.next();
  }

  // 检查 refresh_token cookie
  const refreshToken = request.cookies.get('refresh_token')?.value;
  const isAuthenticated = !!refreshToken;
  const isPublicPath = publicPaths.some((path) => pathname.startsWith(path));

  // 未登录访问受保护页面 → 跳转登录页（保留完整 path + query）
  if (!isAuthenticated && !isPublicPath) {
    const searchParams = new URLSearchParams();
    const next = pathname + search;
    if (next !== '/') {
      searchParams.set('next', next);
    }
    const loginUrl = buildRedirectUrl(request, '/login/', searchParams);
    return NextResponse.redirect(loginUrl);
  }

  // 已登录访问登录/注册页 → 跳转工作台
  if (isAuthenticated && isPublicPath) {
    const dashboardUrl = buildRedirectUrl(request, '/');
    return NextResponse.redirect(dashboardUrl);
  }

  return NextResponse.next();
}

export const config = {
  matcher: ['/((?!_next/static|_next/image|favicon.ico).*)'],
};
