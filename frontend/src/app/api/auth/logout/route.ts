import { NextResponse } from 'next/server';
import { clearAuthCookies, getAuthCookies } from '@/lib/auth/cookies';

const BACKEND = process.env.BACKEND_URL || 'http://localhost:8000';

export async function POST() {
  const { accessToken, refreshToken } = await getAuthCookies();

  // Call backend to blacklist the refresh token
  if (refreshToken) {
    try {
      await fetch(`${BACKEND}/api/v1/auth/logout/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(accessToken ? { Authorization: `Bearer ${accessToken}` } : {}),
        },
        body: JSON.stringify({ refresh: refreshToken }),
      });
    } catch {
      // Backend may be unreachable; still clear cookies
    }
  }

  await clearAuthCookies();
  return NextResponse.json({ success: true });
}
