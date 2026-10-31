'use client';

import { useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import Link from 'next/link';
import { ArrowLeft } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import { ItemImages } from '@/components/items/item-images';
import { ItemInfo } from '@/components/items/item-info';
import { ItemActions } from '@/components/items/item-actions';
import { PageHelp } from '@/components/ui/help-tooltip';
import { BarcodeModal } from '@/components/operations/barcode-modal';
import { useItem, useDeactivateItem } from '@/lib/hooks/use-items';

export default function ItemDetailPage() {
  const params = useParams();
  const router = useRouter();
  const itemId = Number(params.id);
  
  const { data: item, isLoading, refetch } = useItem(itemId);
  const { mutate: deactivateItem, isPending: isDeactivating } = useDeactivateItem();
  
  const [barcodeOpen, setBarcodeOpen] = useState(false);
  
  const handleSuccess = () => {
    refetch();
  };
  
  const handleDeactivate = () => {
    deactivateItem(itemId, {
      onSuccess: () => {
        router.push('/items');
      },
    });
  };
  
  if (isLoading) {
    return <ItemDetailSkeleton />;
  }
  
  if (!item) {
    return (
      <div className="text-center py-12">
        <p className="text-muted-foreground mb-4">物品不存在</p>
        <Button asChild variant="outline">
          <Link href="/items">返回列表</Link>
        </Button>
      </div>
    );
  }
  
  return (
    <div className="space-y-6">
      {/* 返回按钮和帮助 */}
      <div className="flex items-center justify-between">
        <Button asChild variant="ghost" size="sm">
          <Link href="/items">
            <ArrowLeft className="h-4 w-4 mr-2" />
            返回列表
          </Link>
        </Button>
        <PageHelp
          title="物品详情使用指南"
          tips={[
            '左侧可上传和管理物品图片',
            '点击图片可设为主图或删除',
            '没有的物品直接删除',
          ]}
        />
      </div>
      
      <div className="grid lg:grid-cols-3 gap-6">
        {/* 左侧：图片 */}
        <div className="lg:col-span-1">
          <Card>
            <CardContent className="p-4">
              <ItemImages 
                itemId={itemId} 
                images={item.images || []} 
                onUpdate={handleSuccess} 
              />
            </CardContent>
          </Card>
        </div>
        
        {/* 右侧：信息和操作 */}
        <div className="lg:col-span-2 space-y-6">
          <Card>
            <CardContent className="p-6">
              <ItemInfo item={item} />
            </CardContent>
          </Card>
          
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">操作</CardTitle>
            </CardHeader>
            <CardContent>
              <ItemActions
                item={item}
                onGenerateBarcode={() => setBarcodeOpen(true)}
                onDeactivate={handleDeactivate}
              />
            </CardContent>
          </Card>
        </div>
      </div>
      
      {/* 弹窗 */}
      <BarcodeModal
        item={item}
        open={barcodeOpen}
        onOpenChange={setBarcodeOpen}
        onSuccess={handleSuccess}
      />
    </div>
  );
}

function ItemDetailSkeleton() {
  return (
    <div className="space-y-6">
      <Skeleton className="h-8 w-24" />
      <div className="grid lg:grid-cols-3 gap-6">
        <div className="lg:col-span-1">
          <Card>
            <CardContent className="p-4">
              <Skeleton className="aspect-square w-full" />
            </CardContent>
          </Card>
        </div>
        <div className="lg:col-span-2 space-y-6">
          <Card>
            <CardContent className="p-6 space-y-4">
              <Skeleton className="h-8 w-1/2" />
              <Skeleton className="h-4 w-full" />
              <Skeleton className="h-4 w-3/4" />
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
