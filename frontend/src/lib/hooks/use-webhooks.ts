'use client';

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { apiFetch, json } from '../api/client';

export interface WebhookEndpoint {
  id: number;
  url: string;
  name: string;
  secret: string;
  events: string[];
  is_active: boolean;
  created_by: number | null;
  created_at: string;
  updated_at: string;
}

export interface WebhookEvent {
  value: string;
  label: string;
}

export interface WebhookTestResult {
  success: boolean;
  status_code: number | null;
  message: string;
}

const key = ['webhooks'];
const invalidate = (qc: ReturnType<typeof useQueryClient>) => () =>
  qc.invalidateQueries({ queryKey: key });

export function useWebhooks() {
  return useQuery({
    queryKey: key,
    queryFn: () =>
      apiFetch<WebhookEndpoint[]>('/system-settings/webhooks/'),
  });
}

export function useWebhookEvents() {
  return useQuery({
    queryKey: ['webhook-events'],
    queryFn: () =>
      apiFetch<WebhookEvent[]>('/system-settings/webhooks/events/'),
    staleTime: 60 * 60 * 1000, // 1 hour - rarely changes
  });
}

export function useCreateWebhook() {
  const qc = useQueryClient();
  return useMutation<WebhookEndpoint, Error, Record<string, unknown>>({
    mutationFn: (data) =>
      apiFetch<WebhookEndpoint>('/system-settings/webhooks/', {
        method: 'POST',
        body: json(data),
      }),
    onSuccess: invalidate(qc),
  });
}

export function useUpdateWebhook() {
  const qc = useQueryClient();
  return useMutation<
    WebhookEndpoint,
    Error,
    { id: number; data: Record<string, unknown> }
  >({
    mutationFn: ({ id, data }) =>
      apiFetch<WebhookEndpoint>(`/system-settings/webhooks/${id}/`, {
        method: 'PATCH',
        body: json(data),
      }),
    onSuccess: invalidate(qc),
  });
}

export function useDeleteWebhook() {
  const qc = useQueryClient();
  return useMutation<unknown, Error, number>({
    mutationFn: (id) =>
      apiFetch(`/system-settings/webhooks/${id}/`, { method: 'DELETE' }),
    onSuccess: invalidate(qc),
  });
}

export function useTestWebhook() {
  return useMutation<WebhookTestResult, Error, number>({
    mutationFn: (id) =>
      apiFetch<WebhookTestResult>(`/system-settings/webhooks/${id}/test/`, {
        method: 'POST',
      }),
  });
}
