'use client';
import { useCallback, useMemo, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import type { AuditLog, AuditLogFilters, LoginLog } from '../api/audit';
import type { Paginated } from '../types';
import { apiFetch, queryString } from '../api/client';

const DEFAULT_PAGE_SIZE = 20;

type LoginLogFilters = {
  page?: number;
  page_size?: number;
  username?: string;
  success?: boolean | string;
  date_from?: string;
  date_to?: string;
  [key: string]: unknown;
};

export function useAuditLogs(initial: AuditLogFilters = {}) {
  const initialFilters = useMemo<AuditLogFilters>(
    () => ({ page: 1, page_size: DEFAULT_PAGE_SIZE, ...initial }),
    // The hook owns the filter state after mount; callers should use updateFilters.
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [],
  );
  const [filters, setFilters] = useState<AuditLogFilters>(initialFilters);
  const query = useQuery({
    queryKey: ['audit-logs', filters],
    queryFn: () => apiFetch<Paginated<AuditLog>>(`/audit-logs/${queryString(filters)}`),
  });

  const updateFilters = useCallback((patch: Partial<AuditLogFilters>) => {
    setFilters((current) => ({ ...current, ...patch, page: 1 }));
  }, []);
  const setPage = useCallback((page: number) => {
    setFilters((current) => ({ ...current, page }));
  }, []);
  const resetFilters = useCallback(() => {
    setFilters({ page: 1, page_size: DEFAULT_PAGE_SIZE });
  }, []);

  return { ...query, filters, updateFilters, setPage, resetFilters };
}

export function useLoginLogs(initial: LoginLogFilters = {}) {
  const [filters, setFilters] = useState<LoginLogFilters>({
    page: 1,
    page_size: DEFAULT_PAGE_SIZE,
    ...initial,
  });
  const query = useQuery({
    queryKey: ['login-logs', filters],
    queryFn: () => apiFetch<Paginated<LoginLog>>(`/login-logs/${queryString(filters)}`),
  });
  const setPage = useCallback((page: number) => {
    setFilters((current) => ({ ...current, page }));
  }, []);

  return { ...query, filters, setPage };
}
