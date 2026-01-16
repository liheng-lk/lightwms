'use client';

import { useEffect, useCallback } from 'react';
import { Camera, CameraOff, AlertCircle, Loader2 } from 'lucide-react';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { useBarcodeScanner } from '@/lib/hooks/use-barcode-scanner';

export interface BarcodeScannerProps {
  /** Callback when a barcode is successfully scanned */
  onScan: (barcode: string, format: string) => void;
  /** Callback when an error occurs */
  onError?: (error: Error) => void;
  /** Whether the scanner is enabled */
  enabled: boolean;
  /** Optional className for the container */
  className?: string;
}

/**
 * BarcodeScanner Component
 * 
 * Implements camera preview with barcode scanning functionality.
 * Provides visual feedback (scan frame), audio feedback (beep), and haptic feedback (vibration).
 * Handles camera permission denial gracefully.
 * 
 * Requirements: 2.1, 2.3, 2.4
 */
export function BarcodeScanner({
  onScan,
  onError,
  enabled,
  className,
}: BarcodeScannerProps) {
  const {
    startScanning,
    stopScanning,
    isScanning,
    hasPermission,
    error,
    videoRef,
  } = useBarcodeScanner({
    onScan,
    onError,
  });

  // Auto-start scanning when enabled
  useEffect(() => {
    if (enabled && !isScanning && hasPermission !== false) {
      startScanning();
    } else if (!enabled && isScanning) {
      stopScanning();
    }
  }, [enabled, isScanning, hasPermission, startScanning, stopScanning]);

  // Handle retry permission request
  const handleRetryPermission = useCallback(async () => {
    await startScanning();
  }, [startScanning]);

  // Permission denied state (Requirement 2.4)
  if (hasPermission === false) {
    return (
      <div className={cn('flex flex-col items-center justify-center p-8 text-center', className)}>
        <div className="rounded-full bg-destructive/10 p-4 mb-4">
          <CameraOff className="h-8 w-8 text-destructive" />
        </div>
        <h3 className="text-lg font-semibold mb-2">摄像头权限被拒绝</h3>
        <p className="text-muted-foreground text-sm mb-4 max-w-xs">
          请在浏览器设置中允许访问摄像头，或使用下方的手动输入功能
        </p>
        <Button variant="outline" onClick={handleRetryPermission}>
          <Camera className="mr-2 h-4 w-4" />
          重新请求权限
        </Button>
      </div>
    );
  }

  // Error state
  if (error && !isScanning) {
    return (
      <div className={cn('flex flex-col items-center justify-center p-8 text-center', className)}>
        <div className="rounded-full bg-destructive/10 p-4 mb-4">
          <AlertCircle className="h-8 w-8 text-destructive" />
        </div>
        <h3 className="text-lg font-semibold mb-2">扫描出错</h3>
        <p className="text-muted-foreground text-sm mb-4 max-w-xs">{error}</p>
        <Button variant="outline" onClick={handleRetryPermission}>
          重试
        </Button>
      </div>
    );
  }

  return (
    <div className={cn('relative overflow-hidden rounded-lg bg-black', className)}>
      {/* Video preview (Requirement 2.1) */}
      <video
        ref={videoRef}
        autoPlay
        playsInline
        muted
        className="w-full h-full object-cover"
      />

      {/* Scanning overlay with frame */}
      <div className="absolute inset-0 pointer-events-none">
        {/* Semi-transparent overlay */}
        <div className="absolute inset-0 bg-black/40" />
        
        {/* Scan frame cutout */}
        <div className="absolute inset-0 flex items-center justify-center">
          <div className="relative w-64 h-64 sm:w-72 sm:h-72">
            {/* Clear center area */}
            <div className="absolute inset-0 bg-transparent" 
                 style={{ 
                   boxShadow: '0 0 0 9999px rgba(0, 0, 0, 0.4)',
                 }} 
            />
            
            {/* Corner markers */}
            <div className="absolute top-0 left-0 w-8 h-8 border-t-4 border-l-4 border-primary rounded-tl-lg" />
            <div className="absolute top-0 right-0 w-8 h-8 border-t-4 border-r-4 border-primary rounded-tr-lg" />
            <div className="absolute bottom-0 left-0 w-8 h-8 border-b-4 border-l-4 border-primary rounded-bl-lg" />
            <div className="absolute bottom-0 right-0 w-8 h-8 border-b-4 border-r-4 border-primary rounded-br-lg" />
            
            {/* Scanning line animation */}
            {isScanning && (
              <div className="absolute left-2 right-2 h-0.5 bg-primary/80 animate-scan-line" />
            )}
          </div>
        </div>

        {/* Instructions */}
        <div className="absolute bottom-4 left-0 right-0 text-center">
          <p className="text-white text-sm bg-black/50 inline-block px-4 py-2 rounded-full">
            将条码对准扫描框
          </p>
        </div>
      </div>

      {/* Loading state */}
      {!isScanning && enabled && (
        <div className="absolute inset-0 flex items-center justify-center bg-black/60">
          <div className="flex flex-col items-center text-white">
            <Loader2 className="h-8 w-8 animate-spin mb-2" />
            <p className="text-sm">正在启动摄像头...</p>
          </div>
        </div>
      )}

      {/* Paused state */}
      {!enabled && !isScanning && hasPermission === true && (
        <div className="absolute inset-0 flex items-center justify-center bg-black/60">
          <div className="flex flex-col items-center text-white">
            <Camera className="h-8 w-8 mb-2 opacity-50" />
            <p className="text-sm">扫描已暂停</p>
          </div>
        </div>
      )}
    </div>
  );
}
