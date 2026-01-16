'use client';

import { useState, useRef } from 'react';
import { Check, Upload, X, ImagePlus, Loader2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { cn } from '@/lib/utils';
import { useTheme, presetBackgrounds } from '@/providers/theme-provider';

// 最大文件大小 5MB
const MAX_FILE_SIZE = 5 * 1024 * 1024;
// 支持的图片格式
const ACCEPTED_TYPES = ['image/jpeg', 'image/png', 'image/webp', 'image/gif'];

export function BackgroundPicker() {
  const { settings, updateSettings } = useTheme();
  const [customUrl, setCustomUrl] = useState('');
  const [customColor, setCustomColor] = useState(settings.backgroundColor || '#ffffff');
  const [isUploading, setIsUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  
  const handlePresetSelect = (value: string) => {
    updateSettings({
      backgroundImage: value,
      backgroundColor: '',
    });
    setUploadError(null);
  };
  
  const handleCustomUrl = () => {
    if (customUrl.trim()) {
      updateSettings({
        backgroundImage: customUrl.trim(),
        backgroundColor: '',
      });
      setUploadError(null);
    }
  };
  
  const handleColorChange = (color: string) => {
    setCustomColor(color);
    updateSettings({
      backgroundColor: color,
      backgroundImage: '',
    });
    setUploadError(null);
  };
  
  const handleClearBackground = () => {
    updateSettings({
      backgroundImage: '',
      backgroundColor: '',
    });
    setCustomUrl('');
    setCustomColor('#ffffff');
    setUploadError(null);
  };
  
  const handleFileSelect = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    
    setUploadError(null);
    
    // 验证文件类型
    if (!ACCEPTED_TYPES.includes(file.type)) {
      setUploadError('不支持的图片格式，请上传 JPG、PNG、WebP 或 GIF 格式的图片');
      return;
    }
    
    // 验证文件大小
    if (file.size > MAX_FILE_SIZE) {
      setUploadError('图片大小不能超过 5MB');
      return;
    }
    
    setIsUploading(true);
    
    try {
      // 将图片转换为 base64
      const base64 = await fileToBase64(file);
      updateSettings({
        backgroundImage: base64,
        backgroundColor: '',
      });
    } catch (error) {
      setUploadError('图片处理失败，请重试');
    } finally {
      setIsUploading(false);
      // 清空 input 以便可以重复选择同一文件
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
    }
  };
  
  const fileToBase64 = (file: File): Promise<string> => {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = () => {
        if (typeof reader.result === 'string') {
          resolve(reader.result);
        } else {
          reject(new Error('Failed to read file'));
        }
      };
      reader.onerror = () => reject(reader.error);
      reader.readAsDataURL(file);
    });
  };
  
  const currentBackground = settings.backgroundImage || '';
  const isCustomUpload = currentBackground.startsWith('data:image/');
  
  return (
    <div className="space-y-6">
      <div>
        <Label className="text-base font-medium">预设背景</Label>
        <p className="text-sm text-muted-foreground mb-3">选择一个预设的背景样式</p>
        <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
          {presetBackgrounds.map((bg) => (
            <button
              key={bg.id}
              onClick={() => handlePresetSelect(bg.value)}
              className={cn(
                'relative h-20 rounded-lg border-2 transition-all overflow-hidden',
                currentBackground === bg.value
                  ? 'border-primary ring-2 ring-primary/20'
                  : 'border-border hover:border-primary/50'
              )}
              style={{
                background: bg.value || 'var(--background)',
              }}
            >
              {currentBackground === bg.value && (
                <div className="absolute top-1 right-1 bg-primary text-primary-foreground rounded-full p-0.5">
                  <Check className="h-3 w-3" />
                </div>
              )}
              <span className={cn(
                'absolute bottom-1 left-1 text-xs px-1.5 py-0.5 rounded',
                bg.value ? 'bg-black/50 text-white' : 'bg-muted text-muted-foreground'
              )}>
                {bg.name}
              </span>
            </button>
          ))}
        </div>
      </div>
      
      <div>
        <Label className="text-base font-medium">上传背景图片</Label>
        <p className="text-sm text-muted-foreground mb-3">上传本地图片作为背景（支持 JPG、PNG、WebP、GIF，最大 5MB）</p>
        <div className="flex flex-col gap-3">
          <div className="flex items-center gap-3">
            <input
              ref={fileInputRef}
              type="file"
              accept="image/jpeg,image/png,image/webp,image/gif"
              onChange={handleFileSelect}
              className="hidden"
            />
            <Button
              variant="outline"
              onClick={() => fileInputRef.current?.click()}
              disabled={isUploading}
              className="flex-1"
            >
              {isUploading ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  处理中...
                </>
              ) : (
                <>
                  <ImagePlus className="h-4 w-4 mr-2" />
                  选择图片
                </>
              )}
            </Button>
          </div>
          {uploadError && (
            <p className="text-sm text-destructive">{uploadError}</p>
          )}
          {isCustomUpload && (
            <div className="relative h-24 rounded-lg border-2 border-primary ring-2 ring-primary/20 overflow-hidden">
              <img
                src={currentBackground}
                alt="自定义背景"
                className="w-full h-full object-cover"
              />
              <div className="absolute top-1 right-1 bg-primary text-primary-foreground rounded-full p-0.5">
                <Check className="h-3 w-3" />
              </div>
              <span className="absolute bottom-1 left-1 text-xs px-1.5 py-0.5 rounded bg-black/50 text-white">
                自定义图片
              </span>
            </div>
          )}
        </div>
      </div>
      
      <div>
        <Label className="text-base font-medium">自定义背景颜色</Label>
        <p className="text-sm text-muted-foreground mb-3">选择一个纯色作为背景</p>
        <div className="flex items-center gap-3">
          <Input
            type="color"
            value={customColor}
            onChange={(e) => handleColorChange(e.target.value)}
            className="w-16 h-10 p-1 cursor-pointer"
          />
          <Input
            type="text"
            value={customColor}
            onChange={(e) => handleColorChange(e.target.value)}
            placeholder="#ffffff"
            className="flex-1 max-w-32"
          />
          <Button
            variant="outline"
            size="sm"
            onClick={() => handleColorChange(customColor)}
          >
            应用
          </Button>
        </div>
      </div>
      
      <div>
        <Label className="text-base font-medium">自定义背景图片 URL</Label>
        <p className="text-sm text-muted-foreground mb-3">输入图片 URL 作为背景</p>
        <div className="flex items-center gap-3">
          <Input
            type="url"
            value={customUrl}
            onChange={(e) => setCustomUrl(e.target.value)}
            placeholder="https://example.com/image.jpg"
            className="flex-1"
          />
          <Button
            variant="outline"
            size="sm"
            onClick={handleCustomUrl}
            disabled={!customUrl.trim()}
          >
            <Upload className="h-4 w-4 mr-1" />
            应用
          </Button>
        </div>
      </div>
      
      {(settings.backgroundImage || settings.backgroundColor) && (
        <Button
          variant="outline"
          onClick={handleClearBackground}
          className="w-full"
        >
          <X className="h-4 w-4 mr-2" />
          清除背景
        </Button>
      )}
    </div>
  );
}
