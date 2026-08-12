'use client';
import { useMutation,useQuery,useQueryClient } from '@tanstack/react-query';
import type { BorrowRecord,Paginated,ReplenishRecord,TakeRecord } from '../types';
import { apiFetch,json,queryString } from '../api/client';
import { exportBorrowRecords as exportBorrowRecordsApi } from '../api/records';
type Params=Record<string,unknown>;
export const exportBorrowRecords=exportBorrowRecordsApi;
function list<T>(path:string,params:Params){return apiFetch<Paginated<T>>(`${path}${queryString(params)}`);}
export function useBorrowRecords(params:Params={}){return useQuery({queryKey:['borrow-records',params],queryFn:()=>list<BorrowRecord>('/borrow-records/',params)});}
export function useTakeRecords(params:Params={}){return useQuery({queryKey:['take-records',params],queryFn:()=>list<TakeRecord>('/take-records/',params)});}
export function useReplenishRecords(params:Params={}){return useQuery({queryKey:['replenish-records',params],queryFn:()=>list<ReplenishRecord>('/replenish-records/',params)});}
export function useItemBorrowRecords(itemId?:number){return useBorrowRecords({item:itemId,page_size:100});}
export function useItemTakeRecords(itemId?:number){return useTakeRecords({item:itemId,page_size:100});}
export function useItemReplenishRecords(itemId?:number){return useReplenishRecords({item:itemId,page_size:100});}
function delOne(path:string,key:string){const qc=useQueryClient();return useMutation<unknown,Error,number>({mutationFn:(id)=>apiFetch(`${path}${id}/`,{method:'DELETE'}),onSuccess:()=>qc.invalidateQueries({queryKey:[key]})});}
function delMany(path:string,key:string){const qc=useQueryClient();return useMutation<unknown,Error,number[]>({mutationFn:(ids)=>apiFetch(`${path}batch-delete/`,{method:'POST',body:json({ids})}),onSuccess:()=>qc.invalidateQueries({queryKey:[key]})});}
export function useDeleteBorrowRecord(){return delOne('/borrow-records/','borrow-records');}
export function useDeleteTakeRecord(){return delOne('/take-records/','take-records');}
export function useDeleteReplenishRecord(){return delOne('/replenish-records/','replenish-records');}
export function useDeleteBorrowRecords(){return delMany('/borrow-records/','borrow-records');}
export function useDeleteTakeRecords(){return delMany('/take-records/','take-records');}
export function useDeleteReplenishRecords(){return delMany('/replenish-records/','replenish-records');}
