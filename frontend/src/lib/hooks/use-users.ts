'use client';
import { useMutation,useQuery,useQueryClient } from '@tanstack/react-query';
import type { Paginated,User,UserRole } from '../types';
import { apiFetch,json } from '../api/client';
import { getUsers } from '../api/users';
type Params=Record<string,unknown>;
const refresh=(qc:ReturnType<typeof useQueryClient>)=>()=>qc.invalidateQueries({queryKey:['users']});
export function useUsers(params:Params={}){return useQuery({queryKey:['users',params],queryFn:()=>getUsers(params)});}
export function useCreateUser(){const qc=useQueryClient();return useMutation<User,Error,{username:string;password:string;role?:UserRole;phone?:string;email?:string;department?:string}>({mutationFn:(d)=>apiFetch('/users/create/',{method:'POST',body:json(d)}),onSuccess:refresh(qc)});}
export function useDisableUser(){const qc=useQueryClient();return useMutation<unknown,Error,number>({mutationFn:(id)=>apiFetch(`/users/${id}/disable/`,{method:'POST'}),onSuccess:refresh(qc)});}
export function useEnableUser(){const qc=useQueryClient();return useMutation<unknown,Error,number>({mutationFn:(id)=>apiFetch(`/users/${id}/enable/`,{method:'POST'}),onSuccess:refresh(qc)});}
export function useResetPassword(){const qc=useQueryClient();return useMutation<{temporary_password:string},Error,number>({mutationFn:(id)=>apiFetch(`/users/${id}/reset-password/`,{method:'POST'}),onSuccess:refresh(qc)});}
export function useSetUserPassword(){const qc=useQueryClient();return useMutation<unknown,Error,{id:number;password?:string;new_password?:string}>({mutationFn:({id,password,new_password})=>apiFetch(`/users/${id}/set-password/`,{method:'POST',body:json({new_password:new_password??password})}),onSuccess:refresh(qc)});}
export function useUpdateUserRole(){const qc=useQueryClient();return useMutation<unknown,Error,{id:number;role:UserRole}>({mutationFn:({id,role})=>apiFetch(`/users/${id}/update-role/`,{method:'POST',body:json({role})}),onSuccess:refresh(qc)});}
export function useChangePassword(){return useMutation<unknown,Error,{old_password:string;new_password:string}>({mutationFn:(d)=>apiFetch('/users/me/change-password/',{method:'POST',body:json(d)})});}
