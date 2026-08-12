'use client';
import { useMutation,useQuery,useQueryClient } from '@tanstack/react-query';
import type { InviteCode,Paginated,UserRole } from '../types';
import { apiFetch,json,queryString } from '../api/client';
type Params=Record<string,unknown>;
export function useInviteCodes(params:Params={}){return useQuery({queryKey:['invite-codes',params],queryFn:()=>apiFetch<Paginated<InviteCode>>(`/invite-codes/${queryString(params)}`)});}
export function useCreateInviteCode(){const qc=useQueryClient();return useMutation<InviteCode,Error,{max_uses:number;default_role:Exclude<UserRole,'super_admin'>;expires_at:string|null}>({mutationFn:(d)=>apiFetch('/invite-codes/',{method:'POST',body:json(d)}),onSuccess:()=>qc.invalidateQueries({queryKey:['invite-codes']})});}
export function useDeactivateInviteCode(){const qc=useQueryClient();return useMutation<InviteCode,Error,number>({mutationFn:(id)=>apiFetch(`/invite-codes/${id}/`,{method:'PATCH',body:json({is_active:false})}),onSuccess:()=>qc.invalidateQueries({queryKey:['invite-codes']})});}
