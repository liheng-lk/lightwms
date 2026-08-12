'use client';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import type { Paginated, Warehouse } from '../types';
import { apiFetch, json, queryString } from '../api/client';

type WarehouseFilters = {
  page?: number;
  page_size?: number;
  search?: string;
  is_active?: boolean | string;
  [key: string]: unknown;
};

async function fetchWarehouses(params: WarehouseFilters = {}): Promise<Paginated<Warehouse>> {
  const data = await apiFetch<Paginated<Warehouse> | Warehouse[]>(`/warehouses/${queryString(params)}`);
  if (Array.isArray(data)) {
    return { count: data.length, next: null, previous: null, results: data };
  }
  return data;
}

const inv = (qc: ReturnType<typeof useQueryClient>) => () => qc.invalidateQueries({ queryKey: ['warehouses'] });

export function useWarehouses(params: WarehouseFilters = {}) {
  return useQuery({
    queryKey: ['warehouses', params],
    queryFn: () => fetchWarehouses(params),
  });
}

export function useCreateWarehouse() {
  const qc = useQueryClient();
  return useMutation<Warehouse, Error, { code: string; name: string; description?: string }>({
    mutationFn: (data) => apiFetch('/warehouses/', { method: 'POST', body: json(data) }),
    onSuccess: inv(qc),
  });
}

export function useUpdateWarehouse() {
  const qc = useQueryClient();
  return useMutation<Warehouse, Error, { id: number; data: Record<string, unknown> }>({
    mutationFn: ({ id, data }) => apiFetch(`/warehouses/${id}/`, { method: 'PATCH', body: json(data) }),
    onSuccess: inv(qc),
  });
}

export function useDeleteWarehouse() {
  const qc = useQueryClient();
  return useMutation<unknown, Error, number>({
    mutationFn: (id) => apiFetch(`/warehouses/${id}/delete/`, { method: 'DELETE' }),
    onSuccess: inv(qc),
  });
}

export function useDeactivateWarehouse() {
  const qc = useQueryClient();
  return useMutation<unknown, Error, number>({
    mutationFn: (id) => apiFetch(`/warehouses/${id}/deactivate/`, { method: 'POST' }),
    onSuccess: inv(qc),
  });
}

export function useDeleteWarehouses() {
  const qc = useQueryClient();
  return useMutation<unknown, Error, number[]>({
    mutationFn: (ids) => apiFetch('/warehouses/batch-delete/', { method: 'POST', body: json({ ids }) }),
    onSuccess: inv(qc),
  });
}
