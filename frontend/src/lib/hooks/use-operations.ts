'use client';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { apiFetch, json } from '../api/client';
import type { BorrowRecord, ReplenishRecord, TakeRecord } from '../types';
function useInvalidate() { const qc=useQueryClient(); return ()=>Promise.all([qc.invalidateQueries({queryKey:['items']}),qc.invalidateQueries({queryKey:['borrow-records']}),qc.invalidateQueries({queryKey:['take-records']}),qc.invalidateQueries({queryKey:['replenish-records']})]); }
export function useBorrow(){const done=useInvalidate();return useMutation<BorrowRecord,Error,{itemId:number;borrower:number;quantity?:number;expected_return_date:string;notes?:string}>({mutationFn:({itemId,...data})=>apiFetch(`/items/${itemId}/borrow/`,{method:'POST',body:json(data)}),onSuccess:done});}
export function useReturn(){const done=useInvalidate();return useMutation<BorrowRecord,Error,{itemId:number;params?:{borrow_record_id?:number;return_notes?:string;condition?:string}}>({mutationFn:({itemId,params={}})=>apiFetch(`/items/${itemId}/return/`,{method:'POST',body:json(params)}),onSuccess:done});}
export function useTake(){const done=useInvalidate();return useMutation<TakeRecord,Error,{itemId:number;taker:number;quantity:number;notes?:string}>({mutationFn:({itemId,...data})=>apiFetch(`/items/${itemId}/take/`,{method:'POST',body:json(data)}),onSuccess:done});}
export function useReplenish(){const done=useInvalidate();return useMutation<ReplenishRecord,Error,{itemId:number;quantity:number;notes?:string}>({mutationFn:({itemId,...data})=>apiFetch(`/items/${itemId}/replenish/`,{method:'POST',body:json(data)}),onSuccess:done});}
