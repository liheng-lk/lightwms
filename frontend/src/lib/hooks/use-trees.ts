'use client';
import { useMutation,useQuery,useQueryClient } from '@tanstack/react-query';
import type { Category,Location,Warehouse } from '../types';
import { apiFetch,json,queryString } from '../api/client';
async function arrayData<T>(path:string):Promise<T[]>{const d=await apiFetch<T[]|{results:T[]}>(path);return Array.isArray(d)?d:d.results;}
export function useWarehouses(){return useQuery({queryKey:['warehouses'],queryFn:()=>arrayData<Warehouse>('/warehouses/')});}
export function useCategoryTree(){return useQuery({queryKey:['categories','tree'],queryFn:()=>arrayData<Category>('/categories/tree/')});}
export function useCategoryList(params:Record<string,unknown>={}){return useQuery({queryKey:['categories','list',params],queryFn:()=>arrayData<Category>(`/categories/${queryString(params)}`)});}
export function useLocationTree(){return useQuery({queryKey:['locations','tree'],queryFn:()=>arrayData<Location>('/locations/tree/')});}
export function useLocationTreeByWarehouse(warehouseId?:number|null){return useQuery({queryKey:['locations','tree',warehouseId],queryFn:()=>arrayData<Location>(`/locations/tree/${queryString({warehouse:warehouseId})}`),enabled:warehouseId!==null&&warehouseId!==undefined});}
export function useLocationList(params:Record<string,unknown>={}){return useQuery({queryKey:['locations','list',params],queryFn:()=>arrayData<Location>(`/locations/${queryString(params)}`)});}
function invalidate(qc:ReturnType<typeof useQueryClient>, keys:string[]){return ()=>Promise.all(keys.map(k=>qc.invalidateQueries({queryKey:[k]})));}
export function useCreateCategory(){const qc=useQueryClient();return useMutation<Category,Error,any>({mutationFn:(d)=>apiFetch('/categories/',{method:'POST',body:json(d)}),onSuccess:invalidate(qc,['categories'])});}
export function useUpdateCategory(){const qc=useQueryClient();return useMutation<Category,Error,{id:number;data:Record<string,unknown>}>({mutationFn:({id,data})=>apiFetch(`/categories/${id}/`,{method:'PATCH',body:json(data)}),onSuccess:invalidate(qc,['categories'])});}
export function useDeactivateCategory(){const qc=useQueryClient();return useMutation<unknown,Error,number>({mutationFn:(id)=>apiFetch(`/categories/${id}/deactivate/`,{method:'POST'}),onSuccess:invalidate(qc,['categories'])});}
export function useDeleteCategory(){const qc=useQueryClient();return useMutation<unknown,Error,number>({mutationFn:(id)=>apiFetch(`/categories/${id}/delete/`,{method:'DELETE'}),onSuccess:invalidate(qc,['categories'])});}
export function useCreateLocation(){const qc=useQueryClient();return useMutation<Location,Error,any>({mutationFn:(d)=>apiFetch('/locations/',{method:'POST',body:json(d)}),onSuccess:invalidate(qc,['locations'])});}
export function useUpdateLocation(){const qc=useQueryClient();return useMutation<Location,Error,{id:number;data:Record<string,unknown>}>({mutationFn:({id,data})=>apiFetch(`/locations/${id}/`,{method:'PATCH',body:json(data)}),onSuccess:invalidate(qc,['locations'])});}
export function useDeactivateLocation(){const qc=useQueryClient();return useMutation<unknown,Error,number>({mutationFn:(id)=>apiFetch(`/locations/${id}/deactivate/`,{method:'POST'}),onSuccess:invalidate(qc,['locations'])});}
