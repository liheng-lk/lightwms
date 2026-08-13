import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

const publicPaths = ['/login', '/register'];
const passthroughPrefixes = ['/api/', '/media/', '/_next', '/favicon'];

function buildRedirectUrl(
  request: NextRequest,
  pathname: string,
  searchParams?: URLSearchParams
): URL {
  // Keep the origin exactly as the browser used it. In particular, local/LAN
  // access such as http://192.168.1.20:3000 must never lose the explicit port.
  // If an external reverse proxy is used later, that proxy is responsible for
  // forwarding the public Host header correctly.
  const url = new URL(request.url);
  url.pathname = pathname;
  url.search = '';
  if (searchParams) {
    searchParams.forEach((value, key) => url.searchParams.set(key, value));
  }
  return url;
}

export function middleware(request: NextRequest) {
  const { pathname, search } = request.nextUrl;

  if (
    passthroughPrefixes.some((path) => pathname.startsWith(path)) ||
    pathname.includes('.')
  ) {
    return NextResponse.next();
  }

  const refreshToken = request.cookies.get('refresh_token')?.value;
  const isAuthenticated = !!refreshToken;
  const isPublicPath = publicPaths.some((path) => pathname.startsWith(path));

  if (!isAuthenticated && !isPublicPath) {
    const searchParams = new URLSearchParams();
    const next = pathname + search;
    if (next !== '/') searchParams.set('next', next);
    return NextResponse.redirect(buildRedirectUrl(request, '/login/', searchParams));
  }

  if (isAuthenticated && isPublicPath) {
    return NextResponse.redirect(buildRedirectUrl(request, '/'));
  }

  return NextResponse.next();
}

export const config = {
  matcher: ['/((?!_next/static|_next/image|favicon.ico).*)'],
};
