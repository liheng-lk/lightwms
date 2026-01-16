'use client';

import { useState, useCallback, useMemo, useEffect } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import {
  Package,
  MapPin,
  User,
  Loader2,
  AlertCircle,
  CheckCircle2,
  RefreshCw,
  ArrowLeftRight,
  Undo2,
  PackageMinus,
  PackagePlus,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { UserSelect } from '@/components/operations/user-select';
import { useQuickAction, type ActionResult } from '@/lib/hooks/use-quick-action';
import { itemStatusConfig, itemTypeConfig } from '@/lib/types/ui';

/**
 * Props for QuickActionPanel component
 */
export interface QuickActionPanelProps {
  /** Barcode to lookup, null when no barcode scanned */
  barcode: string | null;
  /** Callback when an action is completed */
  onActionComplete?: (result: ActionResult) => void;
  /** Callback when user wants to rescan */
  onRescan?: () => void;
  /** Optional className for the container */
  className?: string;
}

/**
 * Get today's date in YYYY-MM-DD format for min date validation
 */
const getTodayString = () => {
  const today = new Date();
  return today.toISOString().split('T')[0];
};

/**
 * Borrow form schema
 */
const borrowSchema = z.object({
  borrower: z.number({ error: '请选择借用人' }),
  expected_return_date: z.string({ error: '请选择预计归还日期' })
    .min(1, '请选择预计归还日期')
    .refine((date) => {
      const selected = new Date(date);
      const today = new Date();
      today.setHours(0, 0, 0, 0);
      return selected >= today;
    }, '预计归还日期不能早于今天'),
  notes: z.string().optional(),
});

type BorrowFormData = z.infer<typeof borrowSchema>;

/**
 * Take form schema
 */
const takeSchema = z.object({
  taker: z.number({ error: '请选择领用人' }),
  quantity: z.number({ error: '请输入数量' }).min(1, '数量至少为 1'),
  notes: z.string().optional(),
});

type TakeFormData = z.infer<typeof takeSchema>;

/**
 * Replenish form schema
 */
const replenishSchema = z.object({
  quantity: z.number({ error: '请输入数量' }).min(1, '数量至少为 1'),
  notes: z.string().optional(),
});

type ReplenishFormData = z.infer<typeof replenishSchema>;

/**
 * Return form schema
 */
const returnSchema = z.object({
  return_notes: z.string().optional(),
});

type ReturnFormData = z.infer<typeof returnSchema>;

/**
 * Action types for the panel
 */
type ActionType = 'borrow' | 'return' | 'take' | 'replenish' | null;

/**
 * Determine which action buttons to show based on item type and status
 * 
 * Requirements:
 * - 4.1: reusable + available → "借出" button
 * - 4.2: reusable + borrowed → "归还" button
 * - 4.3: consumable + in_stock → "领用" button with quantity
 * - 4.4: consumable → "补货" button with quantity
 */
export function getActionButtons(
  type: 'reusable' | 'consumable',
  status: 'available' | 'borrowed' | 'in_stock' | 'out_of_stock'
): ActionType[] {
  if (type === 'reusable') {
    if (status === 'available') {
      return ['borrow'];
    }
    if (status === 'borrowed') {
      return ['return'];
    }
  }
  
  if (type === 'consumable') {
    if (status === 'in_stock') {
      return ['take', 'replenish'];
    }
    if (status === 'out_of_stock') {
      return ['replenish'];
    }
  }
  
  return [];
}

/**
 * QuickActionPanel Component
 * 
 * Displays item information and action buttons after barcode scanning.
 * Handles borrow, return, take, and replenish operations.
 * 
 * Requirements: 3.2, 4.1, 4.2, 4.3, 4.4, 4.5, 4.6
 */
export function QuickActionPanel({
  barcode,
  onActionComplete,
  onRescan,
  className,
}: QuickActionPanelProps) {
  const {
    item,
    isLoading,
    error,
    isExecuting,
    lookupByBarcode,
    executeBorrow,
    executeReturn,
    executeTake,
    executeReplenish,
    reset,
  } = useQuickAction();

  const [activeAction, setActiveAction] = useState<ActionType>(null);
  const [lastResult, setLastResult] = useState<ActionResult | null>(null);

  // Lookup item when barcode changes
  const handleLookup = useCallback(async () => {
    if (barcode) {
      setLastResult(null);
      setActiveAction(null);
      await lookupByBarcode(barcode);
    }
  }, [barcode, lookupByBarcode]);

  // Auto-lookup when barcode changes
  useEffect(() => {
    if (barcode) {
      handleLookup();
    }
  }, [barcode, handleLookup]);

  // Borrow form
  const borrowForm = useForm<BorrowFormData>({
    resolver: zodResolver(borrowSchema),
    defaultValues: { notes: '' },
  });

  // Take form with dynamic max validation
  const takeForm = useForm<TakeFormData>({
    resolver: zodResolver(
      takeSchema.refine(
        (data) => !item || data.quantity <= (item.quantity ?? 0),
        { message: `数量不能超过当前库存`, path: ['quantity'] }
      )
    ),
    defaultValues: { quantity: 1, notes: '' },
  });

  // Replenish form
  const replenishForm = useForm<ReplenishFormData>({
    resolver: zodResolver(replenishSchema),
    defaultValues: { quantity: 1, notes: '' },
  });

  // Return form
  const returnForm = useForm<ReturnFormData>({
    resolver: zodResolver(returnSchema),
    defaultValues: { return_notes: '' },
  });

  // Get available actions based on item type and status
  const availableActions = useMemo(() => {
    if (!item) return [];
    return getActionButtons(item.type, item.status);
  }, [item]);

  // Handle action completion
  const handleActionComplete = useCallback((result: ActionResult) => {
    setLastResult(result);
    setActiveAction(null);
    onActionComplete?.(result);
    
    // Reset forms
    borrowForm.reset();
    takeForm.reset({ quantity: 1, notes: '' });
    replenishForm.reset({ quantity: 1, notes: '' });
    returnForm.reset();
  }, [onActionComplete, borrowForm, takeForm, replenishForm, returnForm]);

  // Handle borrow submit
  const handleBorrowSubmit = async (data: BorrowFormData) => {
    const result = await executeBorrow(
      data.borrower,
      data.expected_return_date,
      data.notes
    );
    handleActionComplete(result);
  };

  // Handle return submit
  const handleReturnSubmit = async (data: ReturnFormData) => {
    const result = await executeReturn(data.return_notes);
    handleActionComplete(result);
  };

  // Handle take submit
  const handleTakeSubmit = async (data: TakeFormData) => {
    const result = await executeTake(data.taker, data.quantity, data.notes);
    handleActionComplete(result);
  };

  // Handle replenish submit
  const handleReplenishSubmit = async (data: ReplenishFormData) => {
    const result = await executeReplenish(data.quantity, data.notes);
    handleActionComplete(result);
  };

  // Handle rescan
  const handleRescan = useCallback(() => {
    reset();
    setActiveAction(null);
    setLastResult(null);
    onRescan?.();
  }, [reset, onRescan]);

  // No barcode scanned yet
  if (!barcode) {
    return (
      <Card className={cn('', className)}>
        <CardContent className="flex flex-col items-center justify-center py-8 text-center">
          <Package className="h-12 w-12 text-muted-foreground/50 mb-4" />
          <p className="text-muted-foreground">扫描条码或手动输入以查询物品</p>
        </CardContent>
      </Card>
    );
  }

  // Loading state (Requirement 3.4)
  if (isLoading) {
    return (
      <Card className={cn('', className)}>
        <CardContent className="flex flex-col items-center justify-center py-8">
          <Loader2 className="h-8 w-8 animate-spin text-primary mb-4" />
          <p className="text-muted-foreground">正在查询物品...</p>
        </CardContent>
      </Card>
    );
  }

  // Error state (Requirement 3.3)
  if (error) {
    return (
      <Card className={cn('', className)}>
        <CardContent className="flex flex-col items-center justify-center py-8 text-center">
          <div className="rounded-full bg-destructive/10 p-3 mb-4">
            <AlertCircle className="h-6 w-6 text-destructive" />
          </div>
          <p className="font-medium mb-1">{error}</p>
          <p className="text-sm text-muted-foreground mb-4">条码: {barcode}</p>
          <Button variant="outline" onClick={handleRescan}>
            <RefreshCw className="h-4 w-4 mr-2" />
            重新扫描
          </Button>
        </CardContent>
      </Card>
    );
  }

  // No item found
  if (!item) {
    return null;
  }

  const statusConfig = itemStatusConfig[item.status];
  const typeConfig = itemTypeConfig[item.type];

  return (
    <Card className={cn('', className)}>
      {/* Item Info Header (Requirement 3.2) */}
      <CardHeader className="pb-3">
        <div className="flex items-start gap-4">
          {/* Item Image */}
          {item.primary_image?.thumb_256_url ? (
            <img
              src={item.primary_image.thumb_256_url}
              alt={item.name}
              className="w-16 h-16 rounded-lg object-cover flex-shrink-0"
            />
          ) : (
            <div className="w-16 h-16 rounded-lg bg-muted flex items-center justify-center flex-shrink-0">
              <Package className="h-8 w-8 text-muted-foreground" />
            </div>
          )}
          
          <div className="flex-1 min-w-0">
            <CardTitle className="text-lg truncate">{item.name}</CardTitle>
            <CardDescription className="mt-1">
              SKU: {item.sku}
            </CardDescription>
            <div className="flex flex-wrap gap-2 mt-2">
              <Badge variant={typeConfig?.variant || 'outline'}>
                {typeConfig?.label || item.type}
              </Badge>
              <Badge
                variant="outline"
                className={cn(
                  statusConfig?.variant === 'success' && 'bg-green-100 text-green-800',
                  statusConfig?.variant === 'warning' && 'bg-yellow-100 text-yellow-800',
                  statusConfig?.variant === 'destructive' && 'bg-red-100 text-red-800'
                )}
              >
                {statusConfig?.label || item.status}
              </Badge>
            </div>
          </div>
        </div>
      </CardHeader>

      <CardContent className="space-y-4">
        {/* Item Details */}
        <div className="grid grid-cols-2 gap-3 text-sm">
          <div className="flex items-center gap-2 text-muted-foreground">
            <MapPin className="h-4 w-4" />
            <span className="truncate">{item.location_full_path || '未设置位置'}</span>
          </div>
          <div className="flex items-center gap-2 text-muted-foreground">
            <User className="h-4 w-4" />
            <span className="truncate">{item.owner_username || '未知'}</span>
          </div>
          {item.type === 'consumable' && (
            <div className="col-span-2 flex items-center gap-2">
              <Package className="h-4 w-4 text-muted-foreground" />
              <span>库存: <strong>{item.quantity ?? 0}</strong></span>
            </div>
          )}
        </div>

        {/* Success Result (Requirement 4.6) */}
        {lastResult && (
          <div
            className={cn(
              'flex items-center gap-2 p-3 rounded-lg',
              lastResult.success
                ? 'bg-green-50 text-green-800'
                : 'bg-red-50 text-red-800'
            )}
          >
            {lastResult.success ? (
              <CheckCircle2 className="h-5 w-5 flex-shrink-0" />
            ) : (
              <AlertCircle className="h-5 w-5 flex-shrink-0" />
            )}
            <span className="text-sm">{lastResult.message}</span>
          </div>
        )}

        {/* Action Buttons (Requirements 4.1, 4.2, 4.3, 4.4) */}
        {!activeAction && availableActions.length > 0 && (
          <div className="flex flex-wrap gap-2">
            {availableActions.includes('borrow') && (
              <Button
                onClick={() => setActiveAction('borrow')}
                disabled={isExecuting}
                className="flex-1"
              >
                <ArrowLeftRight className="h-4 w-4 mr-2" />
                借出
              </Button>
            )}
            {availableActions.includes('return') && (
              <Button
                onClick={() => setActiveAction('return')}
                disabled={isExecuting}
                className="flex-1"
              >
                <Undo2 className="h-4 w-4 mr-2" />
                归还
              </Button>
            )}
            {availableActions.includes('take') && (
              <Button
                onClick={() => setActiveAction('take')}
                disabled={isExecuting}
                className="flex-1"
              >
                <PackageMinus className="h-4 w-4 mr-2" />
                领用
              </Button>
            )}
            {availableActions.includes('replenish') && (
              <Button
                onClick={() => setActiveAction('replenish')}
                disabled={isExecuting}
                variant="outline"
                className="flex-1"
              >
                <PackagePlus className="h-4 w-4 mr-2" />
                补货
              </Button>
            )}
          </div>
        )}

        {/* Borrow Form */}
        {activeAction === 'borrow' && (
          <form onSubmit={borrowForm.handleSubmit(handleBorrowSubmit)} className="space-y-3">
            <div className="space-y-2">
              <Label>借用人 *</Label>
              <UserSelect
                value={borrowForm.watch('borrower')}
                onChange={(v) => borrowForm.setValue('borrower', v as number)}
                placeholder="选择借用人"
              />
              {borrowForm.formState.errors.borrower && (
                <p className="text-sm text-destructive">
                  {borrowForm.formState.errors.borrower.message}
                </p>
              )}
            </div>
            <div className="space-y-2">
              <Label htmlFor="expected_return_date">预计归还日期 *</Label>
              <Input
                id="expected_return_date"
                type="date"
                min={getTodayString()}
                {...borrowForm.register('expected_return_date')}
              />
              {borrowForm.formState.errors.expected_return_date && (
                <p className="text-sm text-destructive">
                  {borrowForm.formState.errors.expected_return_date.message}
                </p>
              )}
            </div>
            <div className="space-y-2">
              <Label htmlFor="borrow_notes">备注</Label>
              <Textarea
                id="borrow_notes"
                placeholder="例如：用于项目演示"
                {...borrowForm.register('notes')}
              />
            </div>
            <div className="flex gap-2">
              <Button
                type="button"
                variant="outline"
                onClick={() => setActiveAction(null)}
                className="flex-1"
              >
                取消
              </Button>
              <Button type="submit" disabled={isExecuting} className="flex-1">
                {isExecuting ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : null}
                确认借出
              </Button>
            </div>
          </form>
        )}

        {/* Return Form */}
        {activeAction === 'return' && (
          <form onSubmit={returnForm.handleSubmit(handleReturnSubmit)} className="space-y-3">
            <div className="space-y-2">
              <Label htmlFor="return_notes">归还备注</Label>
              <Textarea
                id="return_notes"
                placeholder="例如：已清洁消毒，功能正常"
                {...returnForm.register('return_notes')}
              />
            </div>
            <div className="flex gap-2">
              <Button
                type="button"
                variant="outline"
                onClick={() => setActiveAction(null)}
                className="flex-1"
              >
                取消
              </Button>
              <Button type="submit" disabled={isExecuting} className="flex-1">
                {isExecuting ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : null}
                确认归还
              </Button>
            </div>
          </form>
        )}

        {/* Take Form */}
        {activeAction === 'take' && (
          <form onSubmit={takeForm.handleSubmit(handleTakeSubmit)} className="space-y-3">
            <div className="space-y-2">
              <Label>领用人 *</Label>
              <UserSelect
                value={takeForm.watch('taker')}
                onChange={(v) => takeForm.setValue('taker', v as number)}
                placeholder="选择领用人"
              />
              {takeForm.formState.errors.taker && (
                <p className="text-sm text-destructive">
                  {takeForm.formState.errors.taker.message}
                </p>
              )}
            </div>
            <div className="space-y-2">
              <Label htmlFor="take_quantity">领用数量 * (库存: {item.quantity ?? 0})</Label>
              <Input
                id="take_quantity"
                type="number"
                min={1}
                max={item.quantity ?? 0}
                {...takeForm.register('quantity', { valueAsNumber: true })}
              />
              {takeForm.formState.errors.quantity && (
                <p className="text-sm text-destructive">
                  {takeForm.formState.errors.quantity.message}
                </p>
              )}
            </div>
            <div className="space-y-2">
              <Label htmlFor="take_notes">用途备注</Label>
              <Textarea
                id="take_notes"
                placeholder="例如：部门会议使用"
                {...takeForm.register('notes')}
              />
            </div>
            <div className="flex gap-2">
              <Button
                type="button"
                variant="outline"
                onClick={() => setActiveAction(null)}
                className="flex-1"
              >
                取消
              </Button>
              <Button type="submit" disabled={isExecuting} className="flex-1">
                {isExecuting ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : null}
                确认领用
              </Button>
            </div>
          </form>
        )}

        {/* Replenish Form */}
        {activeAction === 'replenish' && (
          <form onSubmit={replenishForm.handleSubmit(handleReplenishSubmit)} className="space-y-3">
            <div className="space-y-2">
              <Label htmlFor="replenish_quantity">补货数量 *</Label>
              <Input
                id="replenish_quantity"
                type="number"
                min={1}
                {...replenishForm.register('quantity', { valueAsNumber: true })}
              />
              {replenishForm.formState.errors.quantity && (
                <p className="text-sm text-destructive">
                  {replenishForm.formState.errors.quantity.message}
                </p>
              )}
            </div>
            <div className="space-y-2">
              <Label htmlFor="replenish_notes">来源备注</Label>
              <Textarea
                id="replenish_notes"
                placeholder="例如：采购入库"
                {...replenishForm.register('notes')}
              />
            </div>
            <div className="flex gap-2">
              <Button
                type="button"
                variant="outline"
                onClick={() => setActiveAction(null)}
                className="flex-1"
              >
                取消
              </Button>
              <Button type="submit" disabled={isExecuting} className="flex-1">
                {isExecuting ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : null}
                确认补货
              </Button>
            </div>
          </form>
        )}

        {/* Continue Scanning Button (Requirement 4.6) */}
        {lastResult?.success && (
          <Button
            variant="outline"
            onClick={handleRescan}
            className="w-full"
          >
            <RefreshCw className="h-4 w-4 mr-2" />
            继续扫描下一个
          </Button>
        )}
      </CardContent>
    </Card>
  );
}
