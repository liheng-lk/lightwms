'use client';

import { useQuery } from '@tanstack/react-query';
import { apiFetch } from '../api/client';

export interface DashboardStats {
  inventory_trends: Array<{ month: string; count: number }>;
  borrow_trends: Array<{ month: string; count: number }>;
  top_borrowed: Array<{ name: string; sku: string; borrow_count: number }>;
  category_distribution: Array<{ name: string; count: number }>;
  take_trends: Array<{ month: string; count: number; total_quantity: number }>;
  replenish_trends: Array<{ month: string; count: number; total_quantity: number }>;
}

export function useDashboardStats() {
  return useQuery({
    queryKey: ['dashboard', 'stats'],
    queryFn: () => apiFetch<DashboardStats>('/dashboard/stats/'),
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
}
