import type { Paginated, User } from '../types';
import { apiFetch, queryString } from './client';

export async function getUsers(params: Record<string, unknown> = {}): Promise<Paginated<User>> {
  const data = await apiFetch<Paginated<User> | User[]>(`/users/${queryString(params)}`);
  if (Array.isArray(data)) return { count: data.length, next: null, previous: null, results: data };
  return data;
}
