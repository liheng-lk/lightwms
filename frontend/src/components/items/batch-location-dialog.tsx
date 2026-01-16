'use client';

import { useState } from 'react';
import { Loader2, MapPin } from 'lucide-react';
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
import { TreeSelect } from './tree-select';
import { useLocationTree } from '@/lib/hooks/use-trees';
import { batchUpdateLocation } from '@/lib/api/items';
import { toast } from 'sonner';

interface BatchLocationDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  selectedItemIds: number[];
  onSuccess: () => void;
}

export function BatchLocationDialog({
  open,
  onOpenChange,
  selectedItemIds,
  onSuccess,
}: BatchLocationDialogProps) {
  const [locationId, setLocationId] = useState<number | undefined>(undefined);
  const [isSubmitting, setIsSubmitting] = useState(false);
  
  const { data: locationTree, isLoading: isLoadingLocations } = useLocationTree();
  
  const handleSubmit = async () => {
    if (!locationId) {
      toast.error('请选择目标库位');
      return;
    }
    
    setIsSubmitting(true);
    try {
      const result = await batchUpdateLocation(selectedItemIds, locationId);
      toast.success(result.message);
      onOpenChange(false);
      setLocationId(undefined);
      onSuccess();
    } catch (error: unknown) {
      console.error('Batch update location failed:', error);
      const message = error instanceof Error ? error.message : '批量迁移库位失败';
      toast.error(message);
    } finally {
      setIsSubmitting(false);
    }
  };
  
  const handleClose = (open: boolean) => {
    if (!open) {
      setLocationId(undefined);
    }
    onOpenChange(open);
  };
  
  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent className="sm:max-w-[425px]">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <MapPin className="h-5 w-5" />
            批量迁移库位
          </DialogTitle>
          <DialogDescription>
            将选中的 {selectedItemIds.length} 个物品迁移到新库位
          </DialogDescription>
        </DialogHeader>
        
        <div className="grid gap-4 py-4">
          <div className="grid gap-2">
            <Label htmlFor="location">目标库位</Label>
            <TreeSelect
              nodes={locationTree || []}
              value={locationId}
              onChange={setLocationId}
              placeholder="选择目标库位"
              loading={isLoadingLocations}
              showCode
            />
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
            disabled={!locationId || isSubmitting}
          >
            {isSubmitting && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
            确认迁移
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
