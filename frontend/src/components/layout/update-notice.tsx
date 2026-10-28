'use client';

import { useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { CircleArrowUp, Copy, Check, RefreshCw, Loader2, ExternalLink } from 'lucide-react';
import { toast } from 'sonner';
import { Button } from '@/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { apiFetch } from '@/lib/api/client';
import { copyText } from '@/lib/clipboard';

export type VersionStatus = {
  current_version: string;
  latest_version: string | null;
  update_available: boolean;
  update_reason?: 'new_version' | 'image_republished' | null;
  published_at?: string | null;
  build_time?: string | null;
  revision?: string | null;
  image_tag?: string;
  detects_republish?: boolean;
  check_ok: boolean;
  checked_at: string;
  release_url: string;
  message: string;
};

const QUERY_KEY = ['system-version'];
const COMPOSE = 'docker compose -f docker/compose/docker-compose.dockerhub.yml';

function formatTime(value?: string | null) {
  if (!value) return '—';
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString('zh-CN', { hour12: false });
}

function upgradeCommands(status: VersionStatus): string {
  const pinned = status.image_tag && status.image_tag !== 'latest';
  const lines = ['# 1. 先备份（见 BACKUP_RESTORE.md）'];
  if (pinned && status.update_reason === 'new_version' && status.latest_version) {
    lines.push(`# 2. 把 .env 中的 LIGHTWMS_VERSION 改为 ${status.latest_version}`);
  }
  lines.push(`${COMPOSE} pull`, `${COMPOSE} up -d`);
  return lines.join('\n');
}

/** Hook shared by the header button and the user menu. */
export function useVersionStatus(enabled: boolean) {
  return useQuery({
    queryKey: QUERY_KEY,
    queryFn: () => apiFetch<VersionStatus>('/system-settings/version/'),
    enabled,
    staleTime: 30 * 60 * 1000,
    refetchInterval: 30 * 60 * 1000,
    refetchOnWindowFocus: false,
    retry: 1,
  });
}

export function UpdateNoticeDialog({
  open,
  onOpenChange,
  status,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  status: VersionStatus | undefined;
}) {
  const queryClient = useQueryClient();
  const [checking, setChecking] = useState(false);
  const [copied, setCopied] = useState(false);

  const recheck = async () => {
    setChecking(true);
    try {
      const fresh = await apiFetch<VersionStatus>('/system-settings/version/?force=true');
      queryClient.setQueryData(QUERY_KEY, fresh);
      if (!fresh.check_ok) toast.error(fresh.message);
      else toast.success(fresh.update_available ? fresh.message : '当前已是最新版本');
    } catch (err) {
      toast.error(err instanceof Error ? err.message : '检查失败');
    } finally {
      setChecking(false);
    }
  };

  const commands = status ? upgradeCommands(status) : '';
  const copyCommands = async () => {
    if (await copyText(commands)) {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } else {
      toast.error('浏览器不允许自动复制，请手动选中命令复制');
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle>{status?.update_available ? '有可用更新' : '系统版本'}</DialogTitle>
          <DialogDescription>
            {status?.update_reason === 'image_republished'
              ? `镜像标签 ${status.image_tag} 在 ${formatTime(status.published_at)} 重新发布过，比当前运行的镜像更新。`
              : status?.message ?? '正在获取版本信息…'}
          </DialogDescription>
        </DialogHeader>

        {status && (
          <div className="space-y-4 text-sm">
            <dl className="grid grid-cols-[auto,1fr] gap-x-4 gap-y-1">
              <dt className="text-muted-foreground">当前版本</dt>
              <dd>
                v{status.current_version}
                {status.revision ? <span className="text-muted-foreground"> ({status.revision})</span> : null}
              </dd>
              <dt className="text-muted-foreground">最新版本</dt>
              <dd>{status.latest_version ? `v${status.latest_version}` : '—'}</dd>
              <dt className="text-muted-foreground">镜像构建时间</dt>
              <dd>{formatTime(status.build_time)}</dd>
              <dt className="text-muted-foreground">跟踪的标签</dt>
              <dd>{status.image_tag ?? 'latest'}</dd>
              <dt className="text-muted-foreground">上次检查</dt>
              <dd>{formatTime(status.checked_at)}</dd>
            </dl>

            {!status.detects_republish && (
              <p className="text-xs text-muted-foreground">
                当前镜像没有记录构建时间，只能通过版本号判断更新；重新发布同一版本号不会被检测到。
              </p>
            )}

            {status.update_available && (
              <div className="space-y-2">
                <p className="font-medium">升级步骤（在部署目录执行）</p>
                <div className="relative">
                  <pre className="rounded-md bg-muted p-3 pr-12 text-xs overflow-x-auto select-all whitespace-pre">
                    {commands}
                  </pre>
                  <Button
                    variant="ghost"
                    size="icon"
                    className="absolute right-1 top-1"
                    onClick={copyCommands}
                    title="复制命令"
                  >
                    {copied ? <Check className="h-4 w-4 text-green-500" /> : <Copy className="h-4 w-4" />}
                  </Button>
                </div>
                <p className="text-xs text-muted-foreground">
                  后端启动时会自动执行数据库迁移，升级后刷新页面即可。
                </p>
              </div>
            )}
          </div>
        )}

        <DialogFooter className="gap-2 sm:gap-0">
          {status?.release_url && (
            <Button variant="ghost" asChild>
              <a href={status.release_url} target="_blank" rel="noopener noreferrer">
                <ExternalLink className="h-4 w-4 mr-2" />
                查看镜像
              </a>
            </Button>
          )}
          <Button variant="outline" onClick={recheck} disabled={checking}>
            {checking ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : <RefreshCw className="h-4 w-4 mr-2" />}
            立即检查
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

/** Header badge: visible on every screen size (it was hidden on mobile). */
export function UpdateNoticeButton({ status, onClick }: { status?: VersionStatus; onClick: () => void }) {
  if (!status?.update_available) return null;
  const label = status.update_reason === 'image_republished'
    ? '镜像有更新'
    : `新版本 v${status.latest_version}`;
  return (
    <Button
      variant="outline"
      size="sm"
      onClick={onClick}
      title={status.message}
      className="border-primary/50 text-primary"
    >
      <CircleArrowUp className="h-4 w-4 sm:mr-2" />
      <span className="hidden sm:inline">{label}</span>
      <span className="sr-only sm:hidden">{label}</span>
    </Button>
  );
}
