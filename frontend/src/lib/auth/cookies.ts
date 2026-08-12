import { cookies } from 'next/headers';

const ACCESS_COOKIE = 'access_token';
const REFRESH_COOKIE = 'refresh_token';

const baseOptions = {
  httpOnly: true,
  secure: process.env.NODE_ENV === 'production',
  sameSite: 'lax' as const,
  path: '/',
};

export async function getAuthCookies() {
  const store = await cookies();
  return {
    accessToken: store.get(ACCESS_COOKIE)?.value ?? null,
    refreshToken: store.get(REFRESH_COOKIE)?.value ?? null,
  };
}

export async function setAuthCookies(accessToken: string, refreshToken: string) {
  const store = await cookies();
  store.set(ACCESS_COOKIE, accessToken, { ...baseOptions, maxAge: 60 * 30 });
  store.set(REFRESH_COOKIE, refreshToken, { ...baseOptions, maxAge: 60 * 60 * 24 * 7 });
}

export async function clearAuthCookies() {
  const store = await cookies();
  store.set(ACCESS_COOKIE, '', { ...baseOptions, maxAge: 0 });
  store.set(REFRESH_COOKIE, '', { ...baseOptions, maxAge: 0 });
}
