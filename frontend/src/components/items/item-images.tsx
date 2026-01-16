'use client';

import { useState, useRef } from 'react';
import Image from 'next/image';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { 
  Upload, 
  Trash2, 
  Star, 
  Loader2,
  ImageIcon 
} from 'lucide-react';
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
import { useUploadImage, useDeleteImage, useSetPrimaryImage } from '@/lib/hooks/use-items';
import { usePermissions } from '@/lib/hooks/use-permissions';
import { toast } from 'sonner';
import type { ItemImage } from '@/lib/types';

interface ItemImagesProps {
  itemId: number;
  images: ItemImage[];
  onUpdate?: () => void;
}

export function ItemImages({ itemId, images, onUpdate }: ItemImagesProps) {
  const [selectedIndex, setSelectedIndex] = useState(0);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [imageToDelete, setImageToDelete] = useState<ItemImage | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  
  const { canCreate } = usePermissions();
  const uploadMutation = useUploadImage();
  const deleteMutation = useDeleteImage();
  const setPrimaryMutation = useSetPrimaryImage();
  
  // Use canCreate() to check if user can manage images (same permission level)
  const canManageImages = canCreate();
  const isLoading = uploadMutation.isPending || deleteMutation.isPending || setPrimaryMutation.isPending;

  // Convert backend image URL to frontend proxy URL
  const toProxyUrl = (url: string | undefined): string => {
    if (!url) return '';
    // If it's already a relative path, use it directly
    if (url.startsWith('/media/')) {
      return `/api/media${url.replace('/media', '')}`;
    }
    // If it's an absolute URL with /media/, extract the path
    const mediaMatch = url.match(/\/media\/(.+)$/);
    if (mediaMatch) {
      return `/api/media/${mediaMatch[1]}`;
    }
    // If it's just a relative path like "items/2/4/768.webp"
    if (!url.startsWith('http') && !url.startsWith('/')) {
      return `/api/media/${url}`;
    }
    return url;
  };

  // Get image URL with fallback
  const getImageUrl = (img: ItemImage) => {
    const url = img.thumb_768_url || img.thumb_768 || img.original_url || img.original || img.image || '';
    return toProxyUrl(url);
  };
  
  const getThumbUrl = (img: ItemImage) => {
    const url = img.thumb_256_url || img.thumb_256 || img.thumb_768_url || img.thumb_768 || img.image || '';
    return toProxyUrl(url);
  };
  
  // Handle file upload - Requirements 6.1, 6.2
  const handleUploadClick = () => {
    fileInputRef.current?.click();
  };
  
  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    
    // Validate file type
    if (!file.type.startsWith('image/')) {
      toast.error('请选择图片文件');
      return;
    }
    
    // Validate file size (max 10MB)
    const maxSize = 10 * 1024 * 1024;
    if (file.size > maxSize) {
      toast.error('图片大小不能超过 10MB');
      return;
    }
    
    uploadMutation.mutate(
      { itemId, file },
      {
        onSuccess: () => {
          onUpdate?.();
          // Reset file input
          if (fileInputRef.current) {
            fileInputRef.current.value = '';
          }
        },
        onError: () => {
          // Reset file input on error
          if (fileInputRef.current) {
            fileInputRef.current.value = '';
          }
        },
      }
    );
  };
  
  // Handle delete - Requirements 6.5
  const handleDeleteClick = (img: ItemImage) => {
    setImageToDelete(img);
    setDeleteDialogOpen(true);
  };
  
  const handleConfirmDelete = () => {
    if (!imageToDelete) return;
    
    deleteMutation.mutate(
      { itemId, imageId: imageToDelete.id },
      {
        onSuccess: () => {
          setDeleteDialogOpen(false);
          setImageToDelete(null);
          // Adjust selected index if needed
          if (selectedIndex >= images.length - 1 && selectedIndex > 0) {
            setSelectedIndex(selectedIndex - 1);
          }
          onUpdate?.();
        },
      }
    );
  };
  
  // Handle set primary - Requirements 6.4
  const handleSetPrimary = (img: ItemImage) => {
    if (img.is_primary) return;
    
    setPrimaryMutation.mutate(
      { itemId, imageId: img.id },
      {
        onSuccess: () => {
          onUpdate?.();
        },
      }
    );
  };
  
  // Sort images to show primary first
  const sortedImages = [...images].sort((a, b) => {
    if (a.is_primary && !b.is_primary) return -1;
    if (!a.is_primary && b.is_primary) return 1;
    return 0;
  });
  
  const selectedImage = sortedImages[selectedIndex];

  return (
    <div className="space-y-3">
      {/* Hidden file input */}
      <input
        ref={fileInputRef}
        type="file"
        accept="image/*"
        className="hidden"
        onChange={handleFileChange}
      />
      
      {/* Main image display */}
      {sortedImages.length === 0 ? (
        <div className="aspect-square bg-muted rounded-lg flex flex-col items-center justify-center text-muted-foreground gap-2">
          <ImageIcon className="h-12 w-12" />
          <span>暂无图片</span>
          {canManageImages && (
            <Button 
              variant="outline" 
              size="sm" 
              onClick={handleUploadClick}
              disabled={isLoading}
            >
              <Upload className="h-4 w-4 mr-2" />
              上传图片
            </Button>
          )}
        </div>
      ) : (
        <>
          {/* Main image with primary badge */}
          <div className="aspect-square relative bg-muted rounded-lg overflow-hidden">
            <Image
              src={getImageUrl(selectedImage)}
              alt="物品图片"
              fill
              className="object-contain"
              sizes="(max-width: 768px) 100vw, 400px"
            />
            {selectedImage.is_primary && (
              <Badge className="absolute top-2 left-2 bg-yellow-500 hover:bg-yellow-500">
                <Star className="h-3 w-3 mr-1 fill-current" />
                主图
              </Badge>
            )}
            
            {/* Image action buttons */}
            {canManageImages && (
              <div className="absolute bottom-2 right-2 flex gap-1">
                {!selectedImage.is_primary && (
                  <Button
                    size="icon"
                    variant="secondary"
                    className="h-8 w-8"
                    onClick={() => handleSetPrimary(selectedImage)}
                    disabled={isLoading}
                    title="设为主图"
                  >
                    {setPrimaryMutation.isPending ? (
                      <Loader2 className="h-4 w-4 animate-spin" />
                    ) : (
                      <Star className="h-4 w-4" />
                    )}
                  </Button>
                )}
                <Button
                  size="icon"
                  variant="destructive"
                  className="h-8 w-8"
                  onClick={() => handleDeleteClick(selectedImage)}
                  disabled={isLoading}
                  title="删除图片"
                >
                  <Trash2 className="h-4 w-4" />
                </Button>
              </div>
            )}
          </div>

          {/* Thumbnail list - Requirements 6.3 */}
          <div className="flex gap-2 overflow-x-auto pb-2">
            {sortedImages.map((img, index) => (
              <button
                key={img.id}
                onClick={() => setSelectedIndex(index)}
                className={cn(
                  'relative w-16 h-16 rounded-md overflow-hidden flex-shrink-0 border-2',
                  index === selectedIndex
                    ? 'border-primary'
                    : 'border-transparent hover:border-muted-foreground/50'
                )}
              >
                <Image
                  src={getThumbUrl(img)}
                  alt={`缩略图 ${index + 1}`}
                  fill
                  className="object-cover"
                  sizes="64px"
                />
                {img.is_primary && (
                  <div className="absolute top-0.5 right-0.5">
                    <Star className="h-3 w-3 text-yellow-500 fill-yellow-500" />
                  </div>
                )}
              </button>
            ))}
            
            {/* Upload button in thumbnail row */}
            {canManageImages && (
              <button
                onClick={handleUploadClick}
                disabled={isLoading}
                className={cn(
                  'w-16 h-16 rounded-md border-2 border-dashed border-muted-foreground/30',
                  'flex items-center justify-center flex-shrink-0',
                  'hover:border-primary hover:bg-muted/50 transition-colors',
                  isLoading && 'opacity-50 cursor-not-allowed'
                )}
              >
                {uploadMutation.isPending ? (
                  <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
                ) : (
                  <Upload className="h-5 w-5 text-muted-foreground" />
                )}
              </button>
            )}
          </div>
        </>
      )}

      {/* Delete confirmation dialog */}
      <AlertDialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>确认删除图片？</AlertDialogTitle>
            <AlertDialogDescription>
              此操作无法撤销，图片将被永久删除。
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel disabled={deleteMutation.isPending}>取消</AlertDialogCancel>
            <AlertDialogAction 
              onClick={handleConfirmDelete}
              disabled={deleteMutation.isPending}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              {deleteMutation.isPending ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  删除中...
                </>
              ) : (
                '确认删除'
              )}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
