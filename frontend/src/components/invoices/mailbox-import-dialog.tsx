'use client';

import { useEffect, useMemo, useRef, useState } from 'react';
import { Mail, Trash2 } from 'lucide-react';
import { toast } from 'sonner';
import { Button } from '@/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  useDeleteMailbox,
  useImportMailboxAttachment,
  useMailboxAttachments,
  useMailboxes,
  useRecognizeMailboxAttachment,
  useSaveMailbox,
  type MailboxAttachment,
} from '@/lib/hooks/use-mailboxes';

const CATEGORIES = ['采购', '办公用品', '设备', '耗材', '服务', '维修', '其他'];

interface MailboxImportDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onImported?: () => void;
  mode?: 'setup' | 'import';
}

export function MailboxImportDialog({ open, onOpenChange, onImported, mode = 'import' }: MailboxImportDialogProps) {
  const { data: mailboxes = [], isLoading } = useMailboxes(open);
  const saveMailbox = useSaveMailbox();
  const deleteMailbox = useDeleteMailbox();
  const importAttachment = useImportMailboxAttachment();
  const recognizeAttachment = useRecognizeMailboxAttachment();
  const recognized = useRef(new Set<string>());
  const recognizeRef = useRef(recognizeAttachment.mutateAsync);
  recognizeRef.current = recognizeAttachment.mutateAsync;

  const [email, setEmail] = useState('');
  const [secret, setSecret] = useState('');
  const [label, setLabel] = useState('');
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [loadAttachments, setLoadAttachments] = useState(false);
  const [category, setCategory] = useState('采购');
  const [amounts, setAmounts] = useState<Record<string, string>>({});
  const [names, setNames] = useState<Record<string, string>>({});

  const activeId = selectedId ?? mailboxes[0]?.id ?? null;
  const attachmentsQuery = useMailboxAttachments(activeId, open && loadAttachments);

  const rows = useMemo(() => attachmentsQuery.data ?? [], [attachmentsQuery.data]);

  useEffect(() => {
    if (!open || mode !== 'import' || activeId === null) return;
    const images = rows.filter((row) => /\.(jpe?g|png)$/i.test(row.filename) && !row.imported).slice(0, 8);
    let cancelled = false;
    const run = async () => {
      for (const row of images) {
        const key = `${activeId}:${row.uid}:${row.part_index}`;
        if (recognized.current.has(key)) continue;
        recognized.current.add(key);
        try {
          const fields = await recognizeRef.current({
            mailboxId: activeId,
            uid: row.uid,
            part_index: row.part_index,
          });
          if (cancelled) return;
          const rowKey = `${row.uid}:${row.part_index}`;
          if (fields.amount) {
            setAmounts((current) => current[rowKey] ? current : { ...current, [rowKey]: fields.amount || '' });
          }
          if (fields.name) {
            setNames((current) => current[rowKey] ? current : { ...current, [rowKey]: fields.name });
          }
        } catch {
          // Leave the amount blank so it can be typed.
        }
      }
    };
    void run();
    return () => {
      cancelled = true;
    };
  }, [activeId, mode, open, rows]);

  const authorize = async () => {
    try {
      const saved = await saveMailbox.mutateAsync({
        email: email.trim(),
        secret,
        label: label.trim(),
      });
      setSecret('');
      setSelectedId(saved.id);
      setLoadAttachments(false);
      toast.success('邮箱已登录');
    } catch (error) {
      toast.error(error instanceof Error ? error.message : '邮箱授权失败');
    }
  };

  const removeMailbox = async (id: number) => {
    try {
      await deleteMailbox.mutateAsync(id);
      if (selectedId === id) setSelectedId(null);
      toast.success('已取消该邮箱授权');
    } catch (error) {
      toast.error(error instanceof Error ? error.message : '取消授权失败');
    }
  };

  const importOne = async (row: MailboxAttachment) => {
    if (activeId === null) return;
    const key = `${row.uid}:${row.part_index}`;
    const amount = Number(amounts[key]);
    if (!Number.isFinite(amount) || amount < 0) {
      toast.error('请先填写这张发票的金额');
      return;
    }
    try {
      await importAttachment.mutateAsync({
        mailboxId: activeId,
        uid: row.uid,
        part_index: row.part_index,
        name: names[key] || row.filename.replace(/\.[^.]+$/, '') || row.subject || '邮箱发票',
        amount,
        category,
      });
      toast.success(`已上传 ${row.filename}`);
      onImported?.();
    } catch (error) {
      toast.error(error instanceof Error ? error.message : '上传失败');
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-h-[85vh] overflow-y-auto sm:max-w-[680px]">
        <DialogHeader>
          <DialogTitle>{mode === 'setup' ? '我的邮箱' : '从邮箱导入发票'}</DialogTitle>
          <DialogDescription>
            {mode === 'setup'
              ? '每个登录账号用自己的邮箱和登录密码添加邮箱。密码只加密保存在这个账号下，其他用户看不到。'
              : '使用当前账号已经登录的邮箱，读取收件箱里最近 45 天的 PDF、JPG、PNG 附件。'}
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-3 rounded-lg border p-3">
          <p className="text-sm font-medium">登录邮箱</p>
          <div className="grid gap-2 sm:grid-cols-2">
            <Input value={label} onChange={(event) => setLabel(event.target.value)} placeholder="备注，例如公司邮箱" />
            <Input value={email} onChange={(event) => setEmail(event.target.value)} placeholder="邮箱地址" autoComplete="username" />
            <Input
              type="password"
              value={secret}
              onChange={(event) => setSecret(event.target.value)}
              placeholder="登录密码"
              autoComplete="current-password"
              className="sm:col-span-2"
            />
          </div>
          <p className="text-xs text-muted-foreground">
            直接填写邮箱账号和登录密码。QQ、163、Gmail、Outlook 以及公司邮箱都会按域名自动连接。
          </p>
          <Button onClick={authorize} disabled={saveMailbox.isPending || !email.includes('@') || !secret}>
            {saveMailbox.isPending ? '正在登录…' : '登录并保存'}
          </Button>
        </div>

        <div className="space-y-2">
          <p className="text-sm font-medium">已授权邮箱</p>
          {isLoading && <p className="text-sm text-muted-foreground">正在读取…</p>}
          {!isLoading && mailboxes.length === 0 && (
            <p className="text-sm text-muted-foreground">还没有授权邮箱。</p>
          )}
          {mailboxes.map((account) => (
            <div key={account.id} className="flex items-center gap-2 rounded-md border px-3 py-2">
              <button
                type="button"
                className={`min-w-0 flex-1 text-left text-sm ${activeId === account.id ? 'font-semibold' : ''}`}
                onClick={() => {
                  setSelectedId(account.id);
                  setLoadAttachments(false);
                }}
              >
                <span className="block truncate">{account.label || account.email}</span>
                <span className="block truncate text-xs text-muted-foreground">{account.email}</span>
                {account.last_error && <span className="block truncate text-xs text-destructive">{account.last_error}</span>}
              </button>
              <Button variant="ghost" size="icon" onClick={() => removeMailbox(account.id)} aria-label="取消授权">
                <Trash2 className="h-4 w-4" />
              </Button>
            </div>
          ))}
        </div>

        {mode === 'import' && activeId !== null && (
          <div className="space-y-3">
            <div className="flex flex-wrap items-center gap-2">
              <Button variant="outline" onClick={() => setLoadAttachments(true)} disabled={attachmentsQuery.isFetching}>
                <Mail className="mr-2 h-4 w-4" />
                {attachmentsQuery.isFetching ? '正在读取附件…' : '读取发票附件'}
              </Button>
              <Select value={category} onValueChange={setCategory}>
                <SelectTrigger className="w-[140px]"><SelectValue /></SelectTrigger>
                <SelectContent>
                  {CATEGORIES.map((item) => <SelectItem key={item} value={item}>{item}</SelectItem>)}
                </SelectContent>
              </Select>
            </div>
            {attachmentsQuery.isError && (
              <p className="text-sm text-destructive">
                {attachmentsQuery.error instanceof Error ? attachmentsQuery.error.message : '读取失败'}
              </p>
            )}
            {loadAttachments && !attachmentsQuery.isFetching && rows.length === 0 && !attachmentsQuery.isError && (
              <p className="text-sm text-muted-foreground">最近 45 天没有可导入的 PDF、JPG 或 PNG 附件。</p>
            )}
            <div className="space-y-2">
              {rows.map((row) => {
                const key = `${row.uid}:${row.part_index}`;
                return (
                  <div key={key} className="grid gap-2 rounded-md border p-3 sm:grid-cols-[1fr_140px_auto] sm:items-center">
                    <div className="min-w-0">
                      <p className="truncate text-sm font-medium">{row.filename}</p>
                      <p className="truncate text-xs text-muted-foreground">
                        {row.subject || '无主题'} · {row.sender || '未知发件人'} · {Math.ceil(row.size / 1024)} KB
                      </p>
                    </div>
                    <Input
                      inputMode="decimal"
                      placeholder="金额"
                      value={amounts[key] ?? ''}
                      disabled={row.imported}
                      onChange={(event) => setAmounts((current) => ({ ...current, [key]: event.target.value }))}
                    />
                    <Button
                      size="sm"
                      disabled={row.imported || importAttachment.isPending}
                      onClick={() => importOne(row)}
                    >
                      {row.imported ? '已导入' : '上传为发票'}
                    </Button>
                  </div>
                );
              })}
            </div>
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}
