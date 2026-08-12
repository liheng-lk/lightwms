'use client';
import { useQuery } from '@tanstack/react-query';
import type { AuditLog,AuditLogFilters,LoginLog } from '../api/audit';
import type { Paginated } from '../types';
import { apiFetch,queryString } from '../api/client';
export function useAuditLogs(params:AuditLogFilters={}){return useQuery({queryKey:['audit-logs',params],queryFn:()=>apiFetch<Paginated<AuditLog>>(`/audit-logs/${queryString(params)}`)});}
export function useLoginLogs(params:Record<string,unknown>={}){return useQuery({queryKey:['login-logs',params],queryFn:()=>apiFetch<Paginated<LoginLog>>(`/login-logs/${queryString(params)}`)});}
