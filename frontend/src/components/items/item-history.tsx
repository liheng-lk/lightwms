'use client';

import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Skeleton } from '@/components/ui/skeleton';
import { StatusBadge } from '@/components/ui/status-badge';
import { 
  useItemBorrowRecords, 
  useItemTakeRecords, 
  useItemReplenishRecords 
} from '@/lib/hooks/use-records';
import type { BorrowRecord, TakeRecord, ReplenishRecord, Item } from '@/lib/types';

interface ItemHistoryProps {
  itemId: number;
  itemType?: Item['item_type'] | Item['type'];
}

export function ItemHistory({ itemId, itemType }: ItemHistoryProps) {
  const isReusable = itemType === 'reusable';
  const isConsumable = itemType === 'consumable';
  const defaultTab = isConsumable ? 'take' : 'borrow';
  
  return (
    <Tabs defaultValue={defaultTab} className="w-full">
      <TabsList className={`grid w-full ${isConsumable ? 'grid-cols-2' : 'grid-cols-1'}`}>
        {isReusable && <TabsTrigger value="borrow">借用记录</TabsTrigger>}
        {isConsumable && (
          <>
            <TabsTrigger value="take">领用记录</TabsTrigger>
            <TabsTrigger value="replenish">补货记录</TabsTrigger>
          </>
        )}
      </TabsList>
      
      {isReusable && (
        <TabsContent value="borrow">
          <BorrowRecordsList itemId={itemId} />
        </TabsContent>
      )}
      
      {isConsumable && (
        <>
          <TabsContent value="take">
            <TakeRecordsList itemId={itemId} />
          </TabsContent>
          <TabsContent value="replenish">
            <ReplenishRecordsList itemId={itemId} />
          </TabsContent>
        </>
      )}
    </Tabs>
  );
}

function formatDate(dateStr: string) {
  return new Date(dateStr).toLocaleDateString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  });
}

function BorrowRecordsList({ itemId }: { itemId: number }) {
  const { data, isLoading } = useItemBorrowRecords(itemId, { page_size: 10 });
  
  if (isLoading) return <RecordsListSkeleton />;
  const records = data?.results || [];
  if (records.length === 0) {
    return <div className="text-sm text-muted-foreground text-center py-4">暂无借用记录</div>;
  }
  
  return (
    <div className="space-y-3">
      {records.map((record: BorrowRecord) => {
        const raw = record as any;
        const borrowedAt = raw.created_at || raw.borrowed_at;
        const expectedReturn = raw.expected_return_date || raw.expected_return_at;
        const actualReturn = raw.actual_return_datetime || raw.actual_return_at;
        const notes = raw.notes || raw.note;
        const quantity = raw.quantity ?? 1;
        return (
          <div key={record.id} className="flex items-start gap-3 p-3 rounded-lg bg-muted/50">
            <div className="h-2 w-2 rounded-full bg-primary mt-2 flex-shrink-0" />
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2 flex-wrap">
                <span className="font-medium">{record.borrower_username || record.borrower_name}</span>
                <span className="text-sm text-muted-foreground">
                  借用 <span className="font-medium text-foreground">{quantity}</span> 件
                </span>
                <StatusBadge status={record.computed_status} type="borrow" />
              </div>
              {borrowedAt && (
                <p className="text-sm text-muted-foreground mt-1">
                  借出时间：{formatDate(borrowedAt)}
                </p>
              )}
              {expectedReturn && (
                <p className="text-sm text-muted-foreground">
                  预计归还：{formatDate(expectedReturn)}
                </p>
              )}
              {actualReturn && (
                <p className="text-sm text-muted-foreground">
                  实际归还：{formatDate(actualReturn)}
                </p>
              )}
              {notes && (
                <p className="text-sm text-muted-foreground mt-1">
                  备注：{notes}
                </p>
              )}
              {raw.return_notes && (
                <p className="text-sm text-muted-foreground mt-1">
                  归还备注：{raw.return_notes}
                </p>
              )}
              {raw.condition && (
                <p className="text-sm text-muted-foreground mt-1">
                  归还状况：{raw.condition}
                </p>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}

function TakeRecordsList({ itemId }: { itemId: number }) {
  const { data, isLoading } = useItemTakeRecords(itemId, { page_size: 10 });
  
  if (isLoading) return <RecordsListSkeleton />;
  const records = data?.results || [];
  if (records.length === 0) {
    return <div className="text-sm text-muted-foreground text-center py-4">暂无领用记录</div>;
  }
  
  return (
    <div className="space-y-3">
      {records.map((record: TakeRecord) => {
        const raw = record as any;
        const notes = raw.notes || raw.note;
        return (
          <div key={record.id} className="flex items-start gap-3 p-3 rounded-lg bg-muted/50">
            <div className="h-2 w-2 rounded-full bg-orange-500 mt-2 flex-shrink-0" />
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2 flex-wrap">
                <span className="font-medium">{record.taker_username}</span>
                <span className="text-sm text-muted-foreground">
                  领用了 <span className="font-medium text-foreground">{record.quantity}</span> 件
                </span>
              </div>
              {(raw.created_at || raw.taken_at) && (
                <p className="text-sm text-muted-foreground mt-1">
                  领用时间：{formatDate(raw.created_at || raw.taken_at)}
                </p>
              )}
              {notes && (
                <p className="text-sm text-muted-foreground mt-1">
                  用途：{notes}
                </p>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}

function ReplenishRecordsList({ itemId }: { itemId: number }) {
  const { data, isLoading } = useItemReplenishRecords(itemId, { page_size: 10 });
  
  if (isLoading) return <RecordsListSkeleton />;
  const records = data?.results || [];
  if (records.length === 0) {
    return <div className="text-sm text-muted-foreground text-center py-4">暂无补货记录</div>;
  }
  
  return (
    <div className="space-y-3">
      {records.map((record: ReplenishRecord) => {
        const raw = record as any;
        const notes = raw.notes || raw.note;
        return (
          <div key={record.id} className="flex items-start gap-3 p-3 rounded-lg bg-muted/50">
            <div className="h-2 w-2 rounded-full bg-green-500 mt-2 flex-shrink-0" />
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2 flex-wrap">
                <span className="font-medium">{record.operator_username}</span>
                <span className="text-sm text-muted-foreground">
                  补货了 <span className="font-medium text-foreground">{record.quantity}</span> 件
                </span>
              </div>
              {(raw.created_at || raw.replenished_at) && (
                <p className="text-sm text-muted-foreground mt-1">
                  补货时间：{formatDate(raw.created_at || raw.replenished_at)}
                </p>
              )}
              {notes && (
                <p className="text-sm text-muted-foreground mt-1">
                  来源：{notes}
                </p>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}

function RecordsListSkeleton() {
  return (
    <div className="space-y-3">
      {Array.from({ length: 3 }).map((_, i) => (
        <div key={i} className="flex gap-3 p-3">
          <Skeleton className="h-2 w-2 rounded-full mt-2" />
          <div className="flex-1 space-y-2">
            <Skeleton className="h-4 w-3/4" />
            <Skeleton className="h-3 w-1/2" />
          </div>
        </div>
      ))}
    </div>
  );
}
