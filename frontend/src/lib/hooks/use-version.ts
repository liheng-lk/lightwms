'use client';

import { useQuery } from '@tanstack/react-query';
import { apiFetch } from '../api/client';

export interface VersionInfo {
  current_version: string;
  latest_version: string | null;
  update_available: boolean;
  source: string;
  checked_at: string;
  error: string | null;
}

export function useVersionInfo() {
  return useQuery({
    queryKey: ['system', 'version'],
    queryFn: () => apiFetch<VersionInfo>('/version/'),
    staleTime: 30 * 60 * 1000,
    refetchInterval: 30 * 60 * 1000,
    refetchOnWindowFocus: false,
    retry: 1,
  });
}
