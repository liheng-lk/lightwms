'use client';
import { useMutation,useQuery,useQueryClient } from '@tanstack/react-query';
import type { Warehouse } from '../types';
import { apiFetch,json } from '../api/client';
async function fetchWarehouses():Promise<Warehouse[]>{const data=await apiFetch<Warehouse[]|{results:Warehouse[]}>('/warehouses/');return Array.isArray(data)?data:data.results;}
const inv=(qc:ReturnType<typeof useQueryClient>)=>()=>qc.invalidateQueries({queryKey:['warehouses']});
export function useWarehouses(){return useQuery({queryKey:['warehouses'],queryFn:fetchWarehouses});}
export function useCreateWarehouse(){const qc=useQueryClient();return useMutation<Warehouse,Error,{code:string;name:string;description?:string}>({mutationFn:(d)=>apiFetch('/warehouses/',{method:'POST',body:json(d)}),onSuccess:inv(qc)});}
export function useUpdateWarehouse(){const qc=useQueryClient();return useMutation<Warehouse,Error,{id:number;data:Record<string,unknown>}>({mutationFn:({id,data})=>apiFetch(`/warehouses/${id}/`,{method:'PATCH',body:json(data)}),onSuccess:inv(qc)});}
export function useDeleteWarehouse(){const qc=useQueryClient();return useMutation<unknown,Error,number>({mutationFn:(id)=>apiFetch(`/warehouses/${id}/delete/`,{method:'DELETE'}),onSuccess:inv(qc)});}
export function useDeactivateWarehouse(){const qc=useQueryClient();return useMutation<unknown,Error,number>({mutationFn:(id)=>apiFetch(`/warehouses/${id}/deactivate/`,{method:'POST'}),onSuccess:inv(qc)});}
export function useDeleteWarehouses(){const qc=useQueryClient();return useMutation<unknown,Error,number[]>({mutationFn:(ids)=>apiFetch('/warehouses/batch-delete/',{method:'POST',body:json({ids})}),onSuccess:inv(qc)});}
