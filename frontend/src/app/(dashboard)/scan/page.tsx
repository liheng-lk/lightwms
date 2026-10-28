'use client';

import { useState, useCallback, useEffect, useRef } from 'react';
import { ScanLine, Keyboard, ArrowLeft } from 'lucide-react';
import { useRouter } from 'next/navigation';
import { Button } from '@/components/ui/button';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import {
  BarcodeScanner,
  ManualInput,
  QuickActionPanel,
  ScanHistory,
  type ScanRecord,
} from '@/components/scanner';
import type { ActionResult } from '@/lib/hooks/use-quick-action';

function generateId(): string {
  return `${Date.now()}-${Math.random().toString(36).substring(2, 11)}`;
}

interface BarcodeItemResponse {
  name?: string;
}

export default function ScanPage() {
  const router = useRouter();
  const [currentBarcode, setCurrentBarcode] = useState<string | null>(null);
  const [scannerEnabled, setScannerEnabled] = useState(true);
  const [inputMode, setInputMode] = useState<'camera' | 'manual'>('camera');
  const [scanHistory, setScanHistory] = useState<ScanRecord[]>([]);
  const lastScannedRef = useRef<string | null>(null);
  const scanTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  // Camera needs HTTPS/localhost. On a plain-HTTP LAN deployment open the
  // manual tab directly (a USB/Bluetooth scanner gun types into it).
  useEffect(() => {
    if (!window.isSecureContext || !navigator.mediaDevices?.getUserMedia) {
      setInputMode('manual');
      setScannerEnabled(false);
    }
  }, []);

  useEffect(() => {
    return () => {
      if (scanTimeoutRef.current) {
        clearTimeout(scanTimeoutRef.current);
      }
    };
  }, []);

  const handleScan = useCallback((barcode: string, format: string) => {
    if (lastScannedRef.current === barcode) {
      return;
    }

    lastScannedRef.current = barcode;

    if (scanTimeoutRef.current) {
      clearTimeout(scanTimeoutRef.current);
    }

    scanTimeoutRef.current = setTimeout(() => {
      lastScannedRef.current = null;
    }, 2000);

    setScannerEnabled(false);
    setCurrentBarcode(barcode);

    if (process.env.NODE_ENV === 'development') {
      console.debug(`Scanned: ${barcode} (${format})`);
    }
  }, []);

  const handleManualInput = useCallback((barcode: string) => {
    setScannerEnabled(false);
    setCurrentBarcode(barcode);
    setInputMode('camera');
  }, []);

  const handleScanError = useCallback((error: Error) => {
    console.error('Scanner error:', error);
  }, []);

  const handleActionComplete = useCallback(async (result: ActionResult) => {
    const barcode = currentBarcode || '';
    let itemName = barcode ? `条码 ${barcode}` : '未知物品';

    if (barcode) {
      try {
        const response = await fetch(`/api/wms/items/by-barcode/${encodeURIComponent(barcode)}/`, {
          cache: 'no-store',
        });
        if (response.ok) {
          const item = (await response.json()) as BarcodeItemResponse;
          if (item.name) itemName = item.name;
        }
      } catch {
        // History should still be recorded even when the display-name lookup fails.
      }
    }

    const record: ScanRecord = {
      id: generateId(),
      barcode,
      itemName,
      action: result.action,
      result: result.success ? 'success' : 'failed',
      timestamp: new Date(),
      message: result.message,
    };

    setScanHistory((prev) => [record, ...prev]);
  }, [currentBarcode]);

  const handleRescan = useCallback(() => {
    setCurrentBarcode(null);
    lastScannedRef.current = null;
    setScannerEnabled(true);
  }, []);

  const handleClearHistory = useCallback(() => {
    setScanHistory([]);
  }, []);

  const handleBack = useCallback(() => {
    router.back();
  }, [router]);

  return (
    <div className="flex flex-col h-[calc(100vh-8rem)] max-w-2xl mx-auto">
      <div className="flex items-center gap-3 mb-4">
        <Button variant="ghost" size="icon" onClick={handleBack} aria-label="返回上一页" className="min-h-11 min-w-11">
          <ArrowLeft className="h-5 w-5" />
        </Button>
        <div>
          <h1 className="text-xl font-semibold">扫码操作</h1>
          <p className="text-xs text-muted-foreground">扫描后相机会暂停，完成操作或点击重新扫描再继续。</p>
        </div>
      </div>

      <div className="flex-1 flex flex-col gap-4 overflow-hidden">
        <Tabs
          value={inputMode}
          onValueChange={(v) => {
            const mode = v as 'camera' | 'manual';
            setInputMode(mode);
            if (mode === 'manual') setScannerEnabled(false);
            if (mode === 'camera' && !currentBarcode) setScannerEnabled(true);
          }}
          className="flex-shrink-0"
        >
          <TabsList className="grid w-full grid-cols-2 h-11">
            <TabsTrigger value="camera" className="flex h-10 items-center gap-2">
              <ScanLine className="h-4 w-4" />
              摄像头扫描
            </TabsTrigger>
            <TabsTrigger value="manual" className="flex h-10 items-center gap-2">
              <Keyboard className="h-4 w-4" />
              手动输入
            </TabsTrigger>
          </TabsList>

          <TabsContent value="camera" className="mt-4">
            <BarcodeScanner
              onScan={handleScan}
              onError={handleScanError}
              enabled={scannerEnabled && inputMode === 'camera'}
              className="aspect-[4/3] max-h-[300px]"
            />
          </TabsContent>

          <TabsContent value="manual" className="mt-4">
            <ManualInput
              onSubmit={handleManualInput}
              autoFocus={inputMode === 'manual'}
              placeholder="输入条码号..."
            />
          </TabsContent>
        </Tabs>

        <QuickActionPanel
          barcode={currentBarcode}
          onActionComplete={handleActionComplete}
          onRescan={handleRescan}
          className="flex-shrink-0"
        />

        <div className="flex-1 overflow-hidden">
          <ScanHistory
            history={scanHistory}
            onClear={handleClearHistory}
            className="h-full"
          />
        </div>
      </div>
    </div>
  );
}
