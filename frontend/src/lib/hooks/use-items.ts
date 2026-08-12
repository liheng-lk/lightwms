'use client';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import type { Item, ItemImage, Paginated } from '../types';
import { apiFetch, json, queryString } from '../api/client';
import type { GenerateBarcodeResponse } from '../api/items';

type Params = Record<string, unknown>;
const key = ['items'];
const invalidate = (qc: ReturnType<typeof useQueryClient>) => () => qc.invalidateQueries({ queryKey: key });
export function useItems(params: Params = {}) { return useQuery({ queryKey:[...key, params], queryFn:()=>apiFetch<Paginated<Item>>(`/items/${queryString(params)}`) }); }
export function useItem(id?: number) { return useQuery({ queryKey:[...key,id], queryFn:()=>apiFetch<Item>(`/items/${id}/`), enabled:!!id }); }
export function useCreateItem() { const qc=useQueryClient(); return useMutation<Item,Error,Record<string,unknown>>({ mutationFn:(data)=>apiFetch<Item>('/items/',{method:'POST',body:json(data)}), onSuccess:invalidate(qc) }); }
export function useUpdateItem() { const qc=useQueryClient(); return useMutation<Item,Error,{id:number;data:Record<string,unknown>}>({ mutationFn:({id,data})=>apiFetch<Item>(`/items/${id}/`,{method:'PATCH',body:json(data)}), onSuccess:invalidate(qc) }); }
export function useDeleteItem() { const qc=useQueryClient(); return useMutation<unknown,Error,number>({ mutationFn:(id)=>apiFetch(`/items/${id}/delete/`,{method:'DELETE'}), onSuccess:invalidate(qc) }); }
export function useDeactivateItem() { const qc=useQueryClient(); return useMutation<unknown,Error,number>({ mutationFn:(id)=>apiFetch(`/items/${id}/deactivate/`,{method:'POST'}), onSuccess:invalidate(qc) }); }
export function useDeleteItems() { const qc=useQueryClient(); return useMutation<unknown,Error,number[]>({ mutationFn:(ids)=>apiFetch('/items/batch-delete/',{method:'POST',body:json({ids})}), onSuccess:invalidate(qc) }); }
export function useGenerateBarcode() { const qc=useQueryClient(); return useMutation<GenerateBarcodeResponse,Error,number>({ mutationFn:(id)=>apiFetch(`/items/${id}/generate-barcode/`,{method:'POST'}), onSuccess:invalidate(qc) }); }
export function useGenerateBarcodes() { const qc=useQueryClient(); return useMutation<GenerateBarcodeResponse[],Error,number[]>({ mutationFn:(ids)=>Promise.all(ids.map((id)=>apiFetch<GenerateBarcodeResponse>(`/items/${id}/generate-barcode/`,{method:'POST'}))), onSuccess:invalidate(qc) }); }
export function useUploadImage() { const qc=useQueryClient(); return useMutation<ItemImage,Error,any>({ mutationFn:(v)=>{ const itemId=v.itemId??v.item_id??v.id; const file=v.file??v.image; const form=new FormData(); form.append('image',file); if(v.is_primary!==undefined) form.append('is_primary',String(v.is_primary)); return apiFetch<ItemImage>(`/items/${itemId}/images/`,{method:'POST',body:form}); }, onSuccess:invalidate(qc) }); }
export function useDeleteImage() { const qc=useQueryClient(); return useMutation<unknown,Error,any>({ mutationFn:(v)=>apiFetch(`/items/${v.itemId??v.item_id}/images/${v.imageId??v.image_id??v.id}/`,{method:'DELETE'}), onSuccess:invalidate(qc) }); }
export function useSetPrimaryImage() { const qc=useQueryClient(); return useMutation<ItemImage,Error,any>({ mutationFn:(v)=>apiFetch<ItemImage>(`/items/${v.itemId??v.item_id}/images/${v.imageId??v.image_id??v.id}/set-primary/`,{method:'POST'}), onSuccess:invalidate(qc) }); }
