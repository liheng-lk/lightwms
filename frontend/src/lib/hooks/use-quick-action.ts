'use client';

import { useCallback, useState } from 'react';
import type { Item } from '../types';
import { apiFetch, json } from '../api/client';

export type QuickActionType = 'borrow' | 'return' | 'take' | 'replenish';
export interface ActionResult {
  success: boolean;
  action: QuickActionType;
  message: string;
}

type ScannableItem = Omit<Item, 'status'> & {
  status: 'available' | 'borrowed' | 'in_stock' | 'out_of_stock';
};

export function useQuickAction() {
  const [item, setItem] = useState<ScannableItem | null>(null);
  const [isLoading, setLoading] = useState(false);
  const [isExecuting, setExecuting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const lookupByBarcode = useCallback(async (barcode: string) => {
    setLoading(true);
    setError(null);
    try {
      const found = await apiFetch<ScannableItem>(`/items/by-barcode/${encodeURIComponent(barcode)}/`);
      setItem(found);
      return found;
    } catch (err) {
      setItem(null);
      setError(err instanceof Error ? err.message : '未找到物品');
      return null;
    } finally {
      setLoading(false);
    }
  }, []);

  const run = useCallback(
    async (action: QuickActionType, request: () => Promise<unknown>): Promise<ActionResult> => {
      setExecuting(true);
      try {
        await request();
        if (item?.barcode) await lookupByBarcode(item.barcode);
        return {
          success: true,
          action,
          message: {
            borrow: '借出成功',
            return: '归还成功',
            take: '领用成功',
            replenish: '补货成功',
          }[action],
        };
      } catch (err) {
        return {
          success: false,
          action,
          message: err instanceof Error ? err.message : '操作失败',
        };
      } finally {
        setExecuting(false);
      }
    },
    [item?.barcode, lookupByBarcode]
  );

  const executeBorrow = useCallback(
    (borrower: number, expected_return_date: string, notes?: string) =>
      item
        ? run('borrow', () =>
            apiFetch(`/items/${item.id}/borrow/`, {
              method: 'POST',
              body: json({ borrower, quantity: 1, expected_return_date, notes }),
            })
          )
        : Promise.resolve({ success: false, action: 'borrow' as const, message: '未选择物品' }),
    [item, run]
  );

  const executeReturn = useCallback(
    (return_notes?: string) =>
      item
        ? run('return', () =>
            apiFetch(`/items/${item.id}/return/`, {
              method: 'POST',
              body: json({
                ...(item.current_borrow_record_id
                  ? { borrow_record_id: item.current_borrow_record_id }
                  : {}),
                return_notes,
              }),
            })
          )
        : Promise.resolve({ success: false, action: 'return' as const, message: '未选择物品' }),
    [item, run]
  );

  const executeTake = useCallback(
    (taker: number, quantity: number, notes?: string) =>
      item
        ? run('take', () =>
            apiFetch(`/items/${item.id}/take/`, {
              method: 'POST',
              body: json({ taker, quantity, notes }),
            })
          )
        : Promise.resolve({ success: false, action: 'take' as const, message: '未选择物品' }),
    [item, run]
  );

  const executeReplenish = useCallback(
    (quantity: number, notes?: string) =>
      item
        ? run('replenish', () =>
            apiFetch(`/items/${item.id}/replenish/`, {
              method: 'POST',
              body: json({ quantity, notes }),
            })
          )
        : Promise.resolve({ success: false, action: 'replenish' as const, message: '未选择物品' }),
    [item, run]
  );

  const reset = useCallback(() => {
    setItem(null);
    setError(null);
    setLoading(false);
    setExecuting(false);
  }, []);

  return {
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
  };
}
