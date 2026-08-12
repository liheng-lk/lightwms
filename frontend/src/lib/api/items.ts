import { apiFetch, json } from './client';

export interface GenerateBarcodeResponse {
  barcode: string;
  label_png_base64: string;
}

export interface BatchUpdateResponse {
  message: string;
  updated_count?: number;
}

export function batchUpdateLocation(itemIds: number[], locationId: number) {
  return apiFetch<BatchUpdateResponse>('/items/batch-update-location/', {
    method: 'POST', body: json({ ids: itemIds, location: locationId }),
  });
}

export function batchUpdateOwner(itemIds: number[], ownerId: number) {
  return apiFetch<BatchUpdateResponse>('/items/batch-update-owner/', {
    method: 'POST', body: json({ ids: itemIds, owner: ownerId }),
  });
}
