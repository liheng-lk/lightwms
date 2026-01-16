import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

// 公开路径（无需登录）
const publicPaths = ['/login', '/register'];

// API 路径（不拦截）
const apiPaths = ['/api/'];

// 构建正确的重定向 URL（考虑反向代理和 Cloudflare Tunnel）
function buildRedirectUrl(request: NextRequest, pathname: string, searchParams?: URLSearchParams): URL {
  // Cloudflare 会设置 CF-Connecting-IP 和其他 CF- 头
  const isCloudflareTunnel = request.headers.get('cf-connecting-ip') !== null;
  
  // 优先使用 X-Forwarded-Host，否则使用 Host 头
  const forwardedHost = request.headers.get('x-forwarded-host');
  const forwardedProto = request.headers.get('x-forwarded-proto') || (isCloudflareTunnel ? 'https' : 'http');
  
  // Host 头通常包含端口信息（如 10.2.113.101:8080）
  const hostHeader = request.headers.get('host') || 'localhost';
  let host = forwardedHost || hostHeader;
  
  // 如果是 Cloudflare Tunnel，移除端口号（Cloudflare 使用标准 443 端口）
  if (isCloudflareTunnel) {
    host = host.split(':')[0]; // 移除端口号
  } else if (!host.includes(':')) {
    // 如果 host 不包含端口，尝试从 X-Forwarded-Port 获取
    const forwardedPort = request.headers.get('x-forwarded-port');
    if (forwardedPort && forwardedPort !== '80' && forwardedPort !== '443') {
      host = `${host}:${forwardedPort}`;
    }
  }
  
  const url = new URL(`${forwardedProto}://${host}${pathname}`);
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
    // 注意：trailingSlash: true 配置下，路径必须以 / 结尾
    const loginUrl = buildRedirectUrl(request, '/login/', searchParams);
    return NextResponse.redirect(loginUrl);
  }
  
  // 已登录访问登录页 → 跳转首页
  if (isAuthenticated && isPublicPath) {
    // 注意：trailingSlash: true 配置下，路径必须以 / 结尾
    const itemsUrl = buildRedirectUrl(request, '/items/');
    return NextResponse.redirect(itemsUrl);
  }
  
  return NextResponse.next();
}

export const config = {
  matcher: ['/((?!_next/static|_next/image|favicon.ico).*)'],
};
