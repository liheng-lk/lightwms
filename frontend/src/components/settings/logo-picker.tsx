'use client';

import { useState } from 'react';
import { Upload, X, Image as ImageIcon, Loader2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { useTheme } from '@/providers/theme-provider';
import { toast } from 'sonner';

export function LogoPicker() {
  const { settings, refreshLogo } = useTheme();
  const [logoUrl, setLogoUrl] = useState('');
  const [previewError, setPreviewError] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  
  const handleApplyLogo = async () => {
    if (!logoUrl.trim()) return;
    
    setIsSaving(true);
    try {
      const response = await fetch('/api/system-settings/', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ logo_url: logoUrl.trim() }),
      });
      
      if (!response.ok) {
        throw new Error('Failed to save logo URL');
      }
      
      await refreshLogo();
      setLogoUrl('');
      setPreviewError(false);
      toast.success('Logo 已更新');
    } catch (error) {
      console.error('Failed to save logo:', error);
      toast.error('保存 Logo 失败');
    } finally {
      setIsSaving(false);
    }
  };
  
  const handleClearLogo = async () => {
    setIsSaving(true);
    try {
      const response = await fetch('/api/system-settings/', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ logo_url: '' }),
      });
      
      if (!response.ok) {
        throw new Error('Failed to clear logo');
      }
      
      await refreshLogo();
      setLogoUrl('');
      setPreviewError(false);
      toast.success('已恢复默认 Logo');
    } catch (error) {
      console.error('Failed to clear logo:', error);
      toast.error('清除 Logo 失败');
    } finally {
      setIsSaving(false);
    }
  };
  
  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    
    // Validate file size (2MB max)
    if (file.size > 2 * 1024 * 1024) {
      toast.error('文件过大，最大允许 2MB');
      return;
    }
    
    setIsUploading(true);
    try {
      const formData = new FormData();
      formData.append('logo', file);
      
      const response = await fetch('/api/system-settings/upload-logo/', {
        method: 'POST',
        body: formData,
      });
      
      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.message || 'Upload failed');
      }
      
      await refreshLogo();
      setPreviewError(false);
      toast.success('Logo 已上传');
    } catch (error) {
      console.error('Failed to upload logo:', error);
      toast.error(error instanceof Error ? error.message : '上传 Logo 失败');
    } finally {
      setIsUploading(false);
      // Reset file input
      e.target.value = '';
    }
  };
  
  return (
    <div className="space-y-6">
      <div>
        <Label className="text-base font-medium">当前 Logo</Label>
        <p className="text-sm text-muted-foreground mb-3">
          {settings.customLogo ? '已设置自定义 Logo（所有用户可见）' : '使用默认 LightWMS Logo'}
        </p>
        <div className="flex items-center gap-4 p-4 border rounded-lg bg-muted/30">
          {settings.customLogo && !previewError ? (
            <img
              src={settings.customLogo}
              alt="Custom Logo"
              className="h-12 w-auto max-w-[200px] object-contain"
              onError={() => setPreviewError(true)}
            />
          ) : (
            <div className="flex items-center gap-2 text-muted-foreground">
              <ImageIcon className="h-8 w-8" />
              <span className="font-semibold text-lg">LightWMS</span>
            </div>
          )}
        </div>
      </div>
      
      <div>
        <Label className="text-base font-medium">上传 Logo 文件</Label>
        <p className="text-sm text-muted-foreground mb-3">支持 PNG、JPG、SVG 格式，建议尺寸 200x50 像素，最大 2MB</p>
        <div className="flex items-center gap-3">
          <Input
            type="file"
            accept="image/png,image/jpeg,image/svg+xml,image/webp"
            onChange={handleFileUpload}
            className="flex-1"
            disabled={isUploading}
          />
          {isUploading && <Loader2 className="h-4 w-4 animate-spin" />}
        </div>
      </div>
      
      <div>
        <Label className="text-base font-medium">或输入 Logo URL</Label>
        <p className="text-sm text-muted-foreground mb-3">输入图片链接作为 Logo</p>
        <div className="flex items-center gap-3">
          <Input
            type="url"
            value={logoUrl}
            onChange={(e) => setLogoUrl(e.target.value)}
            placeholder="https://example.com/logo.png"
            className="flex-1"
            disabled={isSaving}
          />
          <Button
            variant="outline"
            size="sm"
            onClick={handleApplyLogo}
            disabled={!logoUrl.trim() || isSaving}
          >
            {isSaving ? (
              <Loader2 className="h-4 w-4 animate-spin mr-1" />
            ) : (
              <Upload className="h-4 w-4 mr-1" />
            )}
            应用
          </Button>
        </div>
      </div>
      
      {settings.customLogo && (
        <Button
          variant="outline"
          onClick={handleClearLogo}
          className="w-full"
          disabled={isSaving}
        >
          {isSaving ? (
            <Loader2 className="h-4 w-4 animate-spin mr-2" />
          ) : (
            <X className="h-4 w-4 mr-2" />
          )}
          恢复默认 Logo
        </Button>
      )}
    </div>
  );
}
