'use client';

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { apiFetch, json } from '../api/client';
import type { Invoice } from '../types';

export interface MailboxAccount {
  id: number;
  label: string;
  email: string;
  provider: string;
  imap_host: string;
  imap_port: number;
  last_error: string;
  created_at: string | null;
}

export interface MailboxAttachment {
  uid: string;
  part_index: number;
  filename: string;
  size: number;
  subject: string;
  sender: string;
  sent_at: string;
  imported: boolean;
}

export interface MailboxDraft {
  email: string;
  secret: string;
  provider?: string;
  label?: string;
  imap_host?: string;
  imap_port?: number;
}

export interface MailboxImportInput {
  mailboxId: number;
  uid: string;
  part_index: number;
  name: string;
  amount: number;
  category: string;
  custom_type?: string;
  project?: string;
}

export function useMailboxes(enabled = true) {
  return useQuery({
    queryKey: ['mailboxes'],
    queryFn: () => apiFetch<MailboxAccount[]>('/mailboxes/'),
    enabled,
  });
}

export function useSaveMailbox() {
  const queryClient = useQueryClient();
  return useMutation<MailboxAccount, Error, MailboxDraft>({
    mutationFn: (draft) => apiFetch<MailboxAccount>('/mailboxes/', { method: 'POST', body: json(draft) }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['mailboxes'] }),
  });
}

export function useDeleteMailbox() {
  const queryClient = useQueryClient();
  return useMutation<unknown, Error, number>({
    mutationFn: (id) => apiFetch(`/mailboxes/${id}/`, { method: 'DELETE' }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['mailboxes'] }),
  });
}

export function useMailboxAttachments(mailboxId: number | null, enabled: boolean) {
  return useQuery({
    queryKey: ['mailboxes', mailboxId, 'attachments'],
    queryFn: () => apiFetch<MailboxAttachment[]>(`/mailboxes/${mailboxId}/attachments/?days=45`),
    enabled: enabled && mailboxId !== null,
  });
}

export function useImportMailboxAttachment() {
  const queryClient = useQueryClient();
  return useMutation<Invoice, Error, MailboxImportInput>({
    mutationFn: ({ mailboxId, ...payload }) =>
      apiFetch<Invoice>(`/mailboxes/${mailboxId}/import/`, { method: 'POST', body: json(payload) }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['invoices'] });
      queryClient.invalidateQueries({ queryKey: ['mailboxes'] });
    },
  });
}
