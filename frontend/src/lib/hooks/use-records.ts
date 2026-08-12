'use client';
import { useMutation,useQuery,useQueryClient } from '@tanstack/react-query';
import type { BorrowRecord,Paginated,ReplenishRecord,TakeRecord } from '../types';
import { apiFetch,json,queryString } from '../api/client';
import { exportBorrowRecords as exportBorrowRecordsApi } from '../api/records';
type Params=Record<string,unknown>;
export const exportBorrowRecords=exportBorrowRecordsApi;
function normalizeBorrow(record: BorrowRecord): BorrowRecord { return {...record, borrowed_at:record.borrowed_at??record.created_at, expected_return_at:record.expected_return_at??record.expected_return_date, returned_at:record.returned_at??record.actual_return_datetime, computed_status:record.computed_status??record.status}; }
function normalizeTake(record: TakeRecord): TakeRecord { return {...record, taken_at:record.taken_at??record.created_at, note:record.note??record.notes}; }
function normalizeReplenish(record: ReplenishRecord): ReplenishRecord { return {...record, replenished_at:record.replenished_at??record.created_at, note:record.note??record.notes}; }
async function list<T>(path:string,params:Params,normalize:(value:T)=>T){const data=await apiFetch<Paginated<T>>(`${path}${queryString(params)}`);return {...data,results:data.results.map(normalize)};}
export function useBorrowRecords(params:Params={}){return useQuery({queryKey:['borrow-records',params],queryFn:()=>list<BorrowRecord>('/borrow-records/',params,normalizeBorrow)});}
export function useTakeRecords(params:Params={}){return useQuery({queryKey:['take-records',params],queryFn:()=>list<TakeRecord>('/take-records/',params,normalizeTake)});}
export function useReplenishRecords(params:Params={}){return useQuery({queryKey:['replenish-records',params],queryFn:()=>list<ReplenishRecord>('/replenish-records/',params,normalizeReplenish)});}
export function useItemBorrowRecords(itemId?:number,params:Params={}){return useBorrowRecords({item:itemId,page_size:100,...params});}
export function useItemTakeRecords(itemId?:number,params:Params={}){return useTakeRecords({item:itemId,page_size:100,...params});}
export function useItemReplenishRecords(itemId?:number,params:Params={}){return useReplenishRecords({item:itemId,page_size:100,...params});}
function delOne(path:string,key:string){const qc=useQueryClient();return useMutation<unknown,Error,number>({mutationFn:(id)=>apiFetch(`${path}${id}/`,{method:'DELETE'}),onSuccess:()=>qc.invalidateQueries({queryKey:[key]})});}
function delMany(path:string,key:string){const qc=useQueryClient();return useMutation<unknown,Error,number[]>({mutationFn:(ids)=>apiFetch(`${path}batch-delete/`,{method:'POST',body:json({ids})}),onSuccess:()=>qc.invalidateQueries({queryKey:[key]})});}
export function useDeleteBorrowRecord(){return delOne('/borrow-records/','borrow-records');}
export function useDeleteTakeRecord(){return delOne('/take-records/','take-records');}
export function useDeleteReplenishRecord(){return delOne('/replenish-records/','replenish-records');}
export function useDeleteBorrowRecords(){return delMany('/borrow-records/','borrow-records');}
export function useDeleteTakeRecords(){return delMany('/take-records/','take-records');}
export function useDeleteReplenishRecords(){return delMany('/replenish-records/','replenish-records');}
