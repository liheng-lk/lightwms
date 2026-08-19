'use client';
import { useMutation,useQuery,useQueryClient } from '@tanstack/react-query';
import type { Invoice,InvoiceStatus,Paginated } from '../types';
import { apiDownload,apiFetch,json,queryString } from '../api/client';
type Params=Record<string,unknown>;
type InvoiceUploader={id:number;username:string};
function normalize(invoice:any):Invoice{return {...invoice,amount:Number(invoice.amount)};}
function inv(qc:ReturnType<typeof useQueryClient>){return ()=>qc.invalidateQueries({queryKey:['invoices']});}
export function useInvoices(params:Params={}){return useQuery({queryKey:['invoices',params],queryFn:async()=>{const d=await apiFetch<Paginated<any>>(`/invoices/${queryString(params)}`);return {...d,results:d.results.map(normalize)} as Paginated<Invoice>;}});}
export function useInvoiceCategories(){return useQuery({queryKey:['invoices','categories'],queryFn:()=>apiFetch<string[]>('/invoices/categories/')});}
export function useInvoiceMonths(){return useQuery({queryKey:['invoices','months'],queryFn:()=>apiFetch<string[]>('/invoices/months/')});}
export function useInvoiceUploaders(){return useQuery({queryKey:['invoices','uploaders'],queryFn:()=>apiFetch<InvoiceUploader[]>('/invoices/uploaders/')});}
export function useCreateInvoice(){const qc=useQueryClient();return useMutation<Invoice,Error,any>({mutationFn:async(d)=>{const form=new FormData();for(const [k,v] of Object.entries(d)){if(v===undefined||v===null)continue;if(k==='file'&&v instanceof File)form.append('file',v);else form.append(k,String(v));}return normalize(await apiFetch<any>('/invoices/',{method:'POST',body:form}));},onSuccess:inv(qc)});}
export function useUpdateInvoice(){const qc=useQueryClient();return useMutation<Invoice,Error,{id:number;data:Record<string,unknown>}>({mutationFn:async({id,data})=>normalize(await apiFetch<any>(`/invoices/${id}/`,{method:'PATCH',body:json(data)})),onSuccess:inv(qc)});}
export function useDeleteInvoice(){const qc=useQueryClient();return useMutation<unknown,Error,number>({mutationFn:(id)=>apiFetch(`/invoices/${id}/`,{method:'DELETE'}),onSuccess:inv(qc)});}
export function useUpdateInvoiceStatus(){const qc=useQueryClient();return useMutation<Invoice,Error,{id:number;status:InvoiceStatus}>({mutationFn:async({id,status})=>normalize(await apiFetch<any>(`/invoices/${id}/status/`,{method:'PATCH',body:json({status})})),onSuccess:inv(qc)});}
export function useBatchUpdateInvoiceStatus(){const qc=useQueryClient();return useMutation<unknown,Error,{ids:number[];status:string}>({mutationFn:(d)=>apiFetch('/invoices/batch/status/',{method:'POST',body:json(d)}),onSuccess:inv(qc)});}
export function useBatchDeleteInvoices(){const qc=useQueryClient();return useMutation<unknown,Error,number[]>({mutationFn:(ids)=>apiFetch('/invoices/batch/delete/',{method:'POST',body:json({ids})}),onSuccess:inv(qc)});}
export function useExportInvoices(){return useMutation<void,Error,Params>({mutationFn:(params)=>apiDownload(`/invoices/export/${queryString(params)}`,{},'invoices.zip')});}
export function useExportInvoicesByIds(){return useMutation<void,Error,number[]>({mutationFn:(ids)=>apiDownload('/invoices/export/',{method:'POST',body:json({ids})},'invoices.zip')});}
export function useExportReimbursementExcel(){return useMutation<void,Error,Params>({mutationFn:(params)=>apiDownload(`/invoices/export/reimbursement/${queryString(params)}`,{},'reimbursement.xlsx')});}
