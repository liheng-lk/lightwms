import { NextRequest, NextResponse } from 'next/server';

const BACKEND_URL = process.env.BACKEND_URL || 'http://backend:8000';
const BACKEND_ORIGIN = new URL(BACKEND_URL).origin;
const PUBLIC_PREFIX = '/api/media/';
const BACKEND_PREFIX = '/media/';

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

function buildBackendMediaUrl(request: NextRequest): URL | null {
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

  const url = new URL(`${BACKEND_PREFIX}${encodedPath}`, BACKEND_URL);
  if (url.origin !== BACKEND_ORIGIN || !url.pathname.startsWith(BACKEND_PREFIX)) {
    return null;
  }

  url.search = request.nextUrl.search;
  return url;
}

async function proxyMedia(request: NextRequest, method: 'GET' | 'HEAD') {
  const url = buildBackendMediaUrl(request);
  if (!url) {
    return NextResponse.json({ detail: 'Invalid media path' }, { status: 400 });
  }

  const headers = new Headers();
  for (const name of REQUEST_HEADERS) {
    const value = request.headers.get(name);
    if (value) {
      headers.set(name, value);
    }
  }

  let response: Response;
  try {
    response = await fetch(url.toString(), {
      method,
      headers,
      redirect: 'manual',
      cache: 'no-store',
    });
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
