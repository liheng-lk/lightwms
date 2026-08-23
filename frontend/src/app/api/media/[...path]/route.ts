import { NextRequest, NextResponse } from 'next/server';
import { clearAuthCookies, getAuthCookies, setAuthCookies } from '@/lib/auth/cookies';

const BACKEND_URL = process.env.BACKEND_URL || 'http://backend:8000';
const BACKEND_ORIGIN = new URL(BACKEND_URL).origin;
const PUBLIC_PREFIX = '/api/media/';
const PUBLIC_BACKEND_PREFIX = '/media/';
const PRIVATE_BACKEND_PREFIX = '/api/v1/private-media/';

const REQUEST_HEADERS = [
  'accept',
  'accept-encoding',
  'if-modified-since',
  'if-none-match',
  'range',
] as const;

const RESPONSE_HEADERS = [
  'accept-ranges',
  'cache-control',
  'content-disposition',
  'content-length',
  'content-range',
  'content-type',
  'etag',
  'last-modified',
] as const;

interface MediaTarget {
  url: URL;
  privateInvoice: boolean;
}

function buildBackendMediaTarget(request: NextRequest): MediaTarget | null {
  const pathname = request.nextUrl.pathname;
  if (!pathname.startsWith(PUBLIC_PREFIX)) {
    return null;
  }

  const encodedPath = pathname.slice(PUBLIC_PREFIX.length);
  if (!encodedPath) {
    return null;
  }

  for (const segment of encodedPath.split('/')) {
    let decoded: string;
    try {
      decoded = decodeURIComponent(segment);
    } catch {
      return null;
    }

    if (
      !decoded ||
      decoded === '.' ||
      decoded === '..' ||
      decoded.includes('/') ||
      decoded.includes('\\') ||
      decoded.includes('\0')
    ) {
      return null;
    }
  }

  const privateInvoice = encodedPath.toLowerCase().startsWith('invoices/');
  const backendPrefix = privateInvoice ? PRIVATE_BACKEND_PREFIX : PUBLIC_BACKEND_PREFIX;
  const url = new URL(`${backendPrefix}${encodedPath}`, BACKEND_URL);

  if (url.origin !== BACKEND_ORIGIN || !url.pathname.startsWith(backendPrefix)) {
    return null;
  }

  url.search = request.nextUrl.search;
  return { url, privateInvoice };
}

async function refreshAccessToken(refreshToken: string): Promise<string | null> {
  try {
    const response = await fetch(`${BACKEND_URL}/api/v1/auth/refresh/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refresh: refreshToken }),
      redirect: 'manual',
      cache: 'no-store',
    });
    if (!response.ok) {
      await clearAuthCookies();
      return null;
    }

    const tokens = await response.json();
    if (!tokens?.access || !tokens?.refresh) {
      await clearAuthCookies();
      return null;
    }
    await setAuthCookies(tokens.access, tokens.refresh);
    return tokens.access as string;
  } catch {
    await clearAuthCookies();
    return null;
  }
}

async function proxyMedia(request: NextRequest, method: 'GET' | 'HEAD') {
  const target = buildBackendMediaTarget(request);
  if (!target) {
    return NextResponse.json({ detail: 'Invalid media path' }, { status: 400 });
  }

  const headers = new Headers();
  for (const name of REQUEST_HEADERS) {
    const value = request.headers.get(name);
    if (value) {
      headers.set(name, value);
    }
  }

  let refreshToken: string | null = null;
  if (target.privateInvoice) {
    const auth = await getAuthCookies();
    refreshToken = auth.refreshToken;
    if (!auth.accessToken) {
      return NextResponse.json({ detail: 'Authentication required' }, { status: 401 });
    }
    headers.set('Authorization', `Bearer ${auth.accessToken}`);
  }

  let response: Response;
  try {
    response = await fetch(target.url.toString(), {
      method,
      headers,
      redirect: 'manual',
      cache: 'no-store',
    });

    if (target.privateInvoice && response.status === 401 && refreshToken) {
      const refreshedAccess = await refreshAccessToken(refreshToken);
      if (!refreshedAccess) {
        return NextResponse.json({ detail: 'Authentication required' }, { status: 401 });
      }
      headers.set('Authorization', `Bearer ${refreshedAccess}`);
      response = await fetch(target.url.toString(), {
        method,
        headers,
        redirect: 'manual',
        cache: 'no-store',
      });
    }
  } catch {
    return NextResponse.json({ detail: 'Media backend unavailable' }, { status: 502 });
  }

  if (response.status >= 300 && response.status < 400) {
    return NextResponse.json({ detail: 'Unexpected media redirect' }, { status: 502 });
  }

  const responseHeaders = new Headers();
  for (const name of RESPONSE_HEADERS) {
    const value = response.headers.get(name);
    if (value) {
      responseHeaders.set(name, value);
    }
  }
  responseHeaders.set('X-Content-Type-Options', 'nosniff');
  if (target.privateInvoice) {
    responseHeaders.set('Cache-Control', 'private, no-store');
    responseHeaders.set('X-Robots-Tag', 'noindex, nofollow');
  }

  return new NextResponse(method === 'HEAD' ? null : response.body, {
    status: response.status,
    headers: responseHeaders,
  });
}

export async function GET(request: NextRequest) {
  return proxyMedia(request, 'GET');
}

export async function HEAD(request: NextRequest) {
  return proxyMedia(request, 'HEAD');
}
