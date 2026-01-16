'use client';

import { useState } from 'react';
import { Loader2, User } from 'lucide-react';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Label } from '@/components/ui/label';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { useUsers } from '@/lib/hooks/use-users';
import { batchUpdateOwner } from '@/lib/api/items';
import { toast } from 'sonner';

interface BatchOwnerDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  selectedItemIds: number[];
  onSuccess: () => void;
}

export function BatchOwnerDialog({
  open,
  onOpenChange,
  selectedItemIds,
  onSuccess,
}: BatchOwnerDialogProps) {
  const [ownerId, setOwnerId] = useState<string>('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  
  // Get all active users
  const { data: usersData, isLoading: isLoadingUsers } = useUsers({
    is_active: true,
    page_size: 100,
  });
  
  const users = usersData?.results || [];
  
  const handleSubmit = async () => {
    if (!ownerId) {
      toast.error('请选择新负责人');
      return;
    }
    
    setIsSubmitting(true);
    try {
      const result = await batchUpdateOwner(selectedItemIds, Number(ownerId));
      toast.success(result.message);
      onOpenChange(false);
      setOwnerId('');
      onSuccess();
    } catch (error: unknown) {
      console.error('Batch update owner failed:', error);
      const message = error instanceof Error ? error.message : '批量更改负责人失败';
      toast.error(message);
    } finally {
      setIsSubmitting(false);
    }
  };
  
  const handleClose = (open: boolean) => {
    if (!open) {
      setOwnerId('');
    }
    onOpenChange(open);
  };
  
  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent className="sm:max-w-[425px]">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <User className="h-5 w-5" />
            批量更改负责人
          </DialogTitle>
          <DialogDescription>
            将选中的 {selectedItemIds.length} 个物品的负责人更改为新用户
          </DialogDescription>
        </DialogHeader>
        
        <div className="grid gap-4 py-4">
          <div className="grid gap-2">
            <Label htmlFor="owner">新负责人</Label>
            <Select
              value={ownerId}
              onValueChange={setOwnerId}
              disabled={isLoadingUsers}
            >
              <SelectTrigger>
                <SelectValue placeholder={isLoadingUsers ? '加载中...' : '选择新负责人'} />
              </SelectTrigger>
              <SelectContent>
                {users.map((user) => (
                  <SelectItem key={user.id} value={String(user.id)}>
                    {user.username}
                    {user.department && (
                      <span className="text-muted-foreground ml-2">
                        ({user.department})
                      </span>
                    )}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </div>
        
        <DialogFooter>
          <Button
            variant="outline"
            onClick={() => handleClose(false)}
            disabled={isSubmitting}
          >
            取消
          </Button>
          <Button
            onClick={handleSubmit}
            disabled={!ownerId || isSubmitting}
          >
            {isSubmitting && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
            确认更改
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
