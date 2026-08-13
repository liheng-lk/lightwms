import { ApiError, queryString } from './client';

async function downloadBlob(path: string): Promise<Blob> {
  const response = await fetch(`/api/wms${path}`);
  if (!response.ok) {
    let message = `导出失败 (${response.status})`;
    try { const data = await response.json(); message = data.message || data.detail || message; } catch {}
    throw new ApiError(response.status, message);
  }
  return response.blob();
}
export function exportBorrowRecords(params: Record<string, unknown> = {}) { return downloadBlob(`/export/borrow-records/${queryString(params)}`); }
export function exportTakeRecords(params: Record<string, unknown> = {}) { return downloadBlob(`/export/take-records/${queryString(params)}`); }
export function exportReplenishRecords(params: Record<string, unknown> = {}) { return downloadBlob(`/export/replenish-records/${queryString(params)}`); }
