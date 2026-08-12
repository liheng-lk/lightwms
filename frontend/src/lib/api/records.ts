import { apiDownload, queryString } from './client';

export function exportBorrowRecords(params: Record<string, unknown> = {}) {
  return apiDownload(`/export/borrow-records/${queryString(params)}`, {}, 'borrow-records.xlsx');
}
export function exportTakeRecords(params: Record<string, unknown> = {}) {
  return apiDownload(`/export/take-records/${queryString(params)}`, {}, 'take-records.xlsx');
}
export function exportReplenishRecords(params: Record<string, unknown> = {}) {
  return apiDownload(`/export/replenish-records/${queryString(params)}`, {}, 'replenish-records.xlsx');
}
