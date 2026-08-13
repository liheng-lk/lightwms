'use client';

import { Copy, Check, Ban } from 'lucide-react';
import { useState } from 'react';
import { Table,TableBody,TableCell,TableHead,TableHeader,TableRow } from '@/components/ui/table';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import { Badge } from '@/components/ui/badge';
import { AlertDialog,AlertDialogAction,AlertDialogCancel,AlertDialogContent,AlertDialogDescription,AlertDialogFooter,AlertDialogHeader,AlertDialogTitle,AlertDialogTrigger } from '@/components/ui/alert-dialog';
import { useDeactivateInviteCode } from '@/lib/hooks/use-invite-codes';
import { formatDate } from '@/lib/utils/date';
import type { InviteCode, InviteCodeStatus, UserRole } from '@/lib/types';

interface InviteCodeTableProps { inviteCodes: InviteCode[]; isLoading?: boolean; onDeactivateSuccess?: () => void; }
const statusLabels: Record<InviteCodeStatus,string>={active:'可用',exhausted:'已用完',expired:'已过期',disabled:'已停用'};
const statusVariants: Record<InviteCodeStatus,'default'|'secondary'|'outline'|'destructive'>={active:'default',exhausted:'secondary',expired:'outline',disabled:'destructive'};
const roleLabels: Record<UserRole,string>={super_admin:'超级管理员',item_manager:'物品管理员',read_only_user:'普通用户'};

export function InviteCodeTable({inviteCodes,isLoading,onDeactivateSuccess}:InviteCodeTableProps){
 const [copiedId,setCopiedId]=useState<number|null>(null);const {mutate:deactivateMutation,isPending:isDeactivating}=useDeactivateInviteCode();
 const handleCopyLink=async(code:string,id:number)=>{const registerUrl=`${window.location.origin}/register?code=${code}`;await navigator.clipboard.writeText(registerUrl);setCopiedId(id);setTimeout(()=>setCopiedId(null),2000);};
 const handleDeactivate=(id:number)=>deactivateMutation(id,{onSuccess:()=>onDeactivateSuccess?.()});
 if(isLoading)return <InviteCodeTableSkeleton/>;
 if(inviteCodes.length===0)return <div className="text-center py-12 text-muted-foreground">暂无邀请码数据</div>;
 return <div className="border rounded-lg overflow-hidden"><Table><TableHeader><TableRow><TableHead>邀请码</TableHead><TableHead className="w-[120px]">默认角色</TableHead><TableHead className="w-[100px]">使用次数</TableHead><TableHead className="w-[80px]">状态</TableHead><TableHead className="hidden md:table-cell">过期时间</TableHead><TableHead className="w-[120px]">操作</TableHead></TableRow></TableHeader><TableBody>{inviteCodes.map(inviteCode=><TableRow key={inviteCode.id}><TableCell className="font-mono">{inviteCode.code}</TableCell><TableCell><Badge variant="secondary">{roleLabels[inviteCode.default_role]}</Badge></TableCell><TableCell>{inviteCode.current_uses} / {inviteCode.max_uses}</TableCell><TableCell><Badge variant={statusVariants[inviteCode.status]}>{statusLabels[inviteCode.status]}</Badge></TableCell><TableCell className="hidden md:table-cell text-muted-foreground">{inviteCode.expires_at?formatDate(inviteCode.expires_at):'永不过期'}</TableCell><TableCell><div className="flex items-center gap-1"><Button variant="ghost" size="icon" onClick={()=>handleCopyLink(inviteCode.code,inviteCode.id)} title="复制注册链接">{copiedId===inviteCode.id?<Check className="h-4 w-4 text-green-500"/>:<Copy className="h-4 w-4"/>}</Button>{inviteCode.status==='active'&&<AlertDialog><AlertDialogTrigger asChild><Button variant="ghost" size="icon" title="停用邀请码" disabled={isDeactivating}><Ban className="h-4 w-4"/></Button></AlertDialogTrigger><AlertDialogContent><AlertDialogHeader><AlertDialogTitle>确认停用邀请码</AlertDialogTitle><AlertDialogDescription>确定要停用邀请码「{inviteCode.code}」吗？停用后该邀请码将无法用于注册。</AlertDialogDescription></AlertDialogHeader><AlertDialogFooter><AlertDialogCancel>取消</AlertDialogCancel><AlertDialogAction onClick={()=>handleDeactivate(inviteCode.id)}>确认停用</AlertDialogAction></AlertDialogFooter></AlertDialogContent></AlertDialog>}</div></TableCell></TableRow>)}</TableBody></Table></div>;
}
function InviteCodeTableSkeleton(){return <div className="border rounded-lg overflow-hidden"><Table><TableHeader><TableRow><TableHead>邀请码</TableHead><TableHead className="w-[120px]">默认角色</TableHead><TableHead className="w-[100px]">使用次数</TableHead><TableHead className="w-[80px]">状态</TableHead><TableHead className="hidden md:table-cell">过期时间</TableHead><TableHead className="w-[120px]">操作</TableHead></TableRow></TableHeader><TableBody>{Array.from({length:5}).map((_,i)=><TableRow key={i}><TableCell><Skeleton className="h-4 w-32"/></TableCell><TableCell><Skeleton className="h-5 w-20"/></TableCell><TableCell><Skeleton className="h-4 w-12"/></TableCell><TableCell><Skeleton className="h-5 w-12"/></TableCell><TableCell className="hidden md:table-cell"><Skeleton className="h-4 w-28"/></TableCell><TableCell><Skeleton className="h-8 w-16"/></TableCell></TableRow>)}</TableBody></Table></div>;}
