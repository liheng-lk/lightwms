'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import {
  ArrowLeft,
  Plus,
  Trash2,
  Pencil,
  Play,
  Check,
  X,
  Webhook,
  Loader2,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Checkbox } from '@/components/ui/checkbox';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog';
import { useAuth } from '@/providers/auth-provider';
import {
  useWebhooks,
  useWebhookEvents,
  useCreateWebhook,
  useUpdateWebhook,
  useDeleteWebhook,
  useTestWebhook,
  type WebhookEndpoint,
} from '@/lib/hooks/use-webhooks';

export default function WebhooksPage() {
  const router = useRouter();
  const { user } = useAuth();

  // Redirect non-super_admin
  useEffect(() => {
    if (user && user.role !== 'super_admin') {
      router.push('/items');
    }
  }, [user, router]);

  const { data: webhooks, isLoading } = useWebhooks();
  const { data: eventTypes } = useWebhookEvents();
  const createMutation = useCreateWebhook();
  const updateMutation = useUpdateWebhook();
  const deleteMutation = useDeleteWebhook();
  const testMutation = useTestWebhook();

  const [showCreateDialog, setShowCreateDialog] = useState(false);
  const [editingWebhook, setEditingWebhook] = useState<WebhookEndpoint | null>(null);
  const [deletingId, setDeletingId] = useState<number | null>(null);
  const [testResult, setTestResult] = useState<{ id: number; message: string; success: boolean } | null>(null);

  // Form state
  const [formUrl, setFormUrl] = useState('');
  const [formName, setFormName] = useState('');
  const [formSecret, setFormSecret] = useState('');
  const [formEvents, setFormEvents] = useState<string[]>([]);
  const [formActive, setFormActive] = useState(true);

  const resetForm = () => {
    setFormUrl('');
    setFormName('');
    setFormSecret('');
    setFormEvents([]);
    setFormActive(true);
  };

  const openCreate = () => {
    resetForm();
    setShowCreateDialog(true);
  };

  const openEdit = (webhook: WebhookEndpoint) => {
    setFormUrl(webhook.url);
    setFormName(webhook.name);
    setFormSecret(webhook.secret);
    setFormEvents([...webhook.events]);
    setFormActive(webhook.is_active);
    setEditingWebhook(webhook);
  };

  const handleCreate = () => {
    createMutation.mutate(
      {
        url: formUrl,
        name: formName,
        secret: formSecret,
        events: formEvents,
        is_active: formActive,
      },
      {
        onSuccess: () => {
          setShowCreateDialog(false);
          resetForm();
        },
      },
    );
  };

  const handleUpdate = () => {
    if (!editingWebhook) return;
    updateMutation.mutate(
      {
        id: editingWebhook.id,
        data: {
          url: formUrl,
          name: formName,
          secret: formSecret,
          events: formEvents,
          is_active: formActive,
        },
      },
      {
        onSuccess: () => {
          setEditingWebhook(null);
          resetForm();
        },
      },
    );
  };

  const handleDelete = () => {
    if (deletingId === null) return;
    deleteMutation.mutate(deletingId, {
      onSuccess: () => setDeletingId(null),
    });
  };

  const handleTest = (id: number) => {
    setTestResult(null);
    testMutation.mutate(id, {
      onSuccess: (result) => {
        setTestResult({ id, message: result.message, success: result.success });
      },
      onError: (err) => {
        setTestResult({ id, message: err.message, success: false });
      },
    });
  };

  const toggleEvent = (event: string) => {
    setFormEvents((prev) =>
      prev.includes(event) ? prev.filter((e) => e !== event) : [...prev, event],
    );
  };

  if (!user || user.role !== 'super_admin') {
    return null;
  }

  return (
    <div className="space-y-6 max-w-4xl">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Button variant="ghost" size="icon" onClick={() => router.push('/settings')}>
            <ArrowLeft className="h-4 w-4" />
          </Button>
          <div>
            <h1 className="text-2xl font-bold">Webhook 管理</h1>
            <p className="text-muted-foreground">配置外部系统的事件通知端点</p>
          </div>
        </div>
        <Button onClick={openCreate}>
          <Plus className="h-4 w-4 mr-2" />
          新增端点
        </Button>
      </div>

      {isLoading ? (
        <div className="flex items-center justify-center py-12 text-muted-foreground">
          <Loader2 className="h-5 w-5 animate-spin mr-2" />
          加载中...
        </div>
      ) : !webhooks?.length ? (
        <Card>
          <CardContent className="flex flex-col items-center justify-center py-12 text-muted-foreground">
            <Webhook className="h-12 w-12 mb-4 opacity-30" />
            <p>尚未配置任何 Webhook 端点</p>
            <p className="text-sm mt-1">添加端点后，系统将在物品变动时发送通知</p>
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-4">
          {webhooks.map((webhook) => (
            <Card key={webhook.id}>
              <CardHeader className="pb-3">
                <div className="flex items-start justify-between">
                  <div className="space-y-1">
                    <CardTitle className="text-base flex items-center gap-2">
                      {webhook.name || '未命名端点'}
                      {webhook.is_active ? (
                        <span className="inline-flex items-center rounded-full bg-green-100 px-2 py-0.5 text-xs text-green-700 dark:bg-green-900/30 dark:text-green-400">
                          启用
                        </span>
                      ) : (
                        <span className="inline-flex items-center rounded-full bg-gray-100 px-2 py-0.5 text-xs text-gray-600 dark:bg-gray-800 dark:text-gray-400">
                          停用
                        </span>
                      )}
                    </CardTitle>
                    <CardDescription className="font-mono text-xs break-all">
                      {webhook.url}
                    </CardDescription>
                  </div>
                  <div className="flex items-center gap-1">
                    <Button
                      variant="ghost"
                      size="icon"
                      onClick={() => handleTest(webhook.id)}
                      disabled={testMutation.isPending}
                      title="测试"
                    >
                      <Play className="h-4 w-4" />
                    </Button>
                    <Button
                      variant="ghost"
                      size="icon"
                      onClick={() => openEdit(webhook)}
                      title="编辑"
                    >
                      <Pencil className="h-4 w-4" />
                    </Button>
                    <Button
                      variant="ghost"
                      size="icon"
                      onClick={() => setDeletingId(webhook.id)}
                      className="text-destructive"
                      title="删除"
                    >
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </div>
                </div>
              </CardHeader>
              <CardContent className="pt-0">
                <div className="flex flex-wrap gap-1.5">
                  {webhook.events.map((event) => {
                    const eventLabel =
                      eventTypes?.find((et) => et.value === event)?.label || event;
                    return (
                      <span
                        key={event}
                        className="inline-flex items-center rounded-md border px-2 py-0.5 text-xs"
                      >
                        {eventLabel}
                      </span>
                    );
                  })}
                </div>
                {testResult && testResult.id === webhook.id && (
                  <div
                    className={`mt-3 flex items-center gap-2 rounded-md px-3 py-2 text-sm ${
                      testResult.success
                        ? 'bg-green-50 text-green-700 dark:bg-green-900/20 dark:text-green-400'
                        : 'bg-red-50 text-red-700 dark:bg-red-900/20 dark:text-red-400'
                    }`}
                  >
                    {testResult.success ? (
                      <Check className="h-4 w-4 shrink-0" />
                    ) : (
                      <X className="h-4 w-4 shrink-0" />
                    )}
                    {testResult.message}
                  </div>
                )}
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {/* Create / Edit Dialog */}
      <Dialog
        open={showCreateDialog || !!editingWebhook}
        onOpenChange={(open) => {
          if (!open) {
            setShowCreateDialog(false);
            setEditingWebhook(null);
            resetForm();
          }
        }}
      >
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle>{editingWebhook ? '编辑 Webhook' : '新增 Webhook'}</DialogTitle>
            <DialogDescription>
              {editingWebhook
                ? '修改 Webhook 端点配置'
                : '添加一个新的 Webhook 端点，接收系统事件通知'}
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div>
              <Label>名称</Label>
              <Input
                placeholder="我的通知服务"
                value={formName}
                onChange={(e) => setFormName(e.target.value)}
              />
            </div>
            <div>
              <Label>URL</Label>
              <Input
                placeholder="https://example.com/webhook"
                value={formUrl}
                onChange={(e) => setFormUrl(e.target.value)}
              />
            </div>
            <div>
              <Label>签名密钥（可选）</Label>
              <Input
                placeholder="用于 HMAC-SHA256 签名验证"
                value={formSecret}
                onChange={(e) => setFormSecret(e.target.value)}
              />
            </div>
            <div>
              <Label className="mb-2 block">订阅事件</Label>
              <div className="grid grid-cols-2 gap-2">
                {eventTypes?.map((event) => (
                  <label
                    key={event.value}
                    className="flex items-center gap-2 text-sm cursor-pointer"
                  >
                    <Checkbox
                      checked={formEvents.includes(event.value)}
                      onCheckedChange={() => toggleEvent(event.value)}
                    />
                    {event.label}
                  </label>
                ))}
              </div>
            </div>
            <label className="flex items-center gap-2 text-sm cursor-pointer">
              <Checkbox
                checked={formActive}
                onCheckedChange={(checked) => setFormActive(!!checked)}
              />
              启用此端点
            </label>
          </div>
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => {
                setShowCreateDialog(false);
                setEditingWebhook(null);
                resetForm();
              }}
            >
              取消
            </Button>
            <Button
              onClick={editingWebhook ? handleUpdate : handleCreate}
              disabled={
                !formUrl || formEvents.length === 0 ||
                createMutation.isPending || updateMutation.isPending
              }
            >
              {(createMutation.isPending || updateMutation.isPending)
                ? '保存中...'
                : '保存'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Delete confirmation */}
      <AlertDialog open={deletingId !== null} onOpenChange={(open) => !open && setDeletingId(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>确认删除</AlertDialogTitle>
            <AlertDialogDescription>
              删除后此端点将不再接收任何事件通知，此操作无法撤销。
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>取消</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleDelete}
              disabled={deleteMutation.isPending}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              {deleteMutation.isPending ? '删除中...' : '确认删除'}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
