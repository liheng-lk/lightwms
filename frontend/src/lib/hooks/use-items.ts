'use client';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import type { Item, ItemImage, Paginated } from '../types';
import { apiFetch, json, queryString } from '../api/client';
import type { GenerateBarcodeResponse } from '../api/items';

type Params = Record<string, unknown>;
const key = ['items'];
const invalidate = (qc: ReturnType<typeof useQueryClient>) => () => qc.invalidateQueries({ queryKey: key });

function normalizeImage(image: ItemImage): ItemImage {
  return { ...image, image: image.image ?? image.original_url ?? image.original ?? null };
}
function normalizeItem(item: Item): Item {
  return {
    ...item,
    item_type: item.item_type ?? item.type,
    owner_id: item.owner_id ?? (typeof item.owner === 'number' ? item.owner : null),
    location_name: item.location_name ?? item.location_full_path ?? item.location_code,
    low_stock_threshold: item.low_stock_threshold ?? 0,
    images: item.images?.map(normalizeImage),
  };
}
function normalizePage(data: Paginated<Item>): Paginated<Item> {
  return { ...data, results: data.results.map(normalizeItem) };
}

export function useItems(params: Params = {}) { return useQuery({ queryKey:[...key, params], queryFn:async()=>normalizePage(await apiFetch<Paginated<Item>>(`/items/${queryString(params)}`)) }); }
export function useItem(id?: number) { return useQuery({ queryKey:[...key,id], queryFn:async()=>normalizeItem(await apiFetch<Item>(`/items/${id}/`)), enabled:!!id }); }
export function useCreateItem() { const qc=useQueryClient(); return useMutation<Item,Error,Record<string,unknown>>({ mutationFn:async(data)=>normalizeItem(await apiFetch<Item>('/items/',{method:'POST',body:json(data)})), onSuccess:invalidate(qc) }); }
export function useUpdateItem() { const qc=useQueryClient(); return useMutation<Item,Error,{id:number;data:Record<string,unknown>}>({ mutationFn:async({id,data})=>normalizeItem(await apiFetch<Item>(`/items/${id}/`,{method:'PATCH',body:json(data)})), onSuccess:invalidate(qc) }); }
export function useDeleteItem() { const qc=useQueryClient(); return useMutation<unknown,Error,number>({ mutationFn:(id)=>apiFetch(`/items/${id}/delete/`,{method:'DELETE'}), onSuccess:invalidate(qc) }); }
export function useDeactivateItem() { const qc=useQueryClient(); return useMutation<unknown,Error,number>({ mutationFn:(id)=>apiFetch(`/items/${id}/deactivate/`,{method:'POST'}), onSuccess:invalidate(qc) }); }
export function useDeleteItems() { const qc=useQueryClient(); return useMutation<unknown,Error,number[]>({ mutationFn:(ids)=>apiFetch('/items/batch-delete/',{method:'POST',body:json({ids})}), onSuccess:invalidate(qc) }); }
export function useGenerateBarcode() { const qc=useQueryClient(); return useMutation<GenerateBarcodeResponse,Error,number>({ mutationFn:async(id)=>{const r=await apiFetch<GenerateBarcodeResponse>(`/items/${id}/generate-barcode/`,{method:'POST'});return {...r,barcode_image:r.barcode_image??r.label_png_base64};}, onSuccess:invalidate(qc) }); }
export function useGenerateBarcodes() { const qc=useQueryClient(); return useMutation<GenerateBarcodeResponse[],Error,number[]>({ mutationFn:(ids)=>Promise.all(ids.map(async(id)=>{const r=await apiFetch<GenerateBarcodeResponse>(`/items/${id}/generate-barcode/`,{method:'POST'});return {...r,barcode_image:r.barcode_image??r.label_png_base64};})), onSuccess:invalidate(qc) }); }
export function useUploadImage() { const qc=useQueryClient(); return useMutation<ItemImage,Error,any>({ mutationFn:async(v)=>{ const itemId=v.itemId??v.item_id??v.id; const file=v.file??v.image; const form=new FormData(); form.append('image',file); if(v.is_primary!==undefined) form.append('is_primary',String(v.is_primary)); return normalizeImage(await apiFetch<ItemImage>(`/items/${itemId}/images/`,{method:'POST',body:form})); }, onSuccess:invalidate(qc) }); }
export function useDeleteImage() { const qc=useQueryClient(); return useMutation<unknown,Error,any>({ mutationFn:(v)=>apiFetch(`/items/${v.itemId??v.item_id}/images/${v.imageId??v.image_id??v.id}/`,{method:'DELETE'}), onSuccess:invalidate(qc) }); }
export function useSetPrimaryImage() { const qc=useQueryClient(); return useMutation<ItemImage,Error,any>({ mutationFn:async(v)=>normalizeImage(await apiFetch<ItemImage>(`/items/${v.itemId??v.item_id}/images/${v.imageId??v.image_id??v.id}/set-primary/`,{method:'POST'})), onSuccess:invalidate(qc) }); }
