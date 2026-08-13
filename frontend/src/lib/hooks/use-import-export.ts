'use client';
import { useMutation,useQueryClient } from '@tanstack/react-query';
import { apiDownload,apiFetch,queryString } from '../api/client';
export interface ImportError { row:number; field?:string; message:string; }
export interface ImportResult { total:number; created:number; updated:number; errors:ImportError[]; }
export function useImportItems(){const qc=useQueryClient();return useMutation<ImportResult,Error,File>({mutationFn:(file)=>{const form=new FormData();form.append('file',file);return apiFetch('/items/import/',{method:'POST',body:form});},onSuccess:()=>qc.invalidateQueries({queryKey:['items']})});}
export function useExportItems(){return useMutation<void,Error,Record<string,unknown>>({mutationFn:(params)=>apiDownload(`/items/export/${queryString(params)}`,{},'items.xlsx')});}
export function useDownloadTemplate(){return useMutation<void,Error,void>({mutationFn:()=>apiDownload('/items/import-template/',{},'items-import-template.xlsx')});}
