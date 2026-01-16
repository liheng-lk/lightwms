'use client';

import { useState, useCallback, useRef } from 'react';
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

/**
 * Generate unique ID for scan records
 */
function generateId(): string {
  return `${Date.now()}-${Math.random().toString(36).substring(2, 11)}`;
}

/**
 * Scan Page
 * 
 * Main page for mobile barcode scanning functionality.
 * Integrates scanner, quick action panel, and scan history components.
 * Implements continuous scanning mode.
 * 
 * Requirements: 5.1, 5.2
 * - Provide "continue scanning" option after operation
 * - Reactivate camera when user chooses to continue
 */
export default function ScanPage() {
  const router = useRouter();
  
  // Current scanned barcode
  const [currentBarcode, setCurrentBarcode] = useState<string | null>(null);
  
  // Scanner enabled state for continuous scanning mode (Requirement 5.1, 5.2)
  const [scannerEnabled, setScannerEnabled] = useState(true);
  
  // Input mode: 'camera' or 'manual'
  const [inputMode, setInputMode] = useState<'camera' | 'manual'>('camera');
  
  // Scan history for the session (Requirement 5.3)
  const [scanHistory, setScanHistory] = useState<ScanRecord[]>([]);
  
  // Track last scanned barcode to prevent duplicate scans
  const lastScannedRef = useRef<string | null>(null);
  const scanTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  /**
   * Handle barcode scan from camera
   * Implements debounce to prevent duplicate scans
   */
  const handleScan = useCallback((barcode: string, format: string) => {
    // Prevent duplicate scans within 2 seconds
    if (lastScannedRef.current === barcode) {
      return;
    }
    
    lastScannedRef.current = barcode;
    
    // Clear previous timeout
    if (scanTimeoutRef.current) {
      clearTimeout(scanTimeoutRef.current);
    }
    
    // Reset duplicate prevention after 2 seconds
    scanTimeoutRef.current = setTimeout(() => {
      lastScannedRef.current = null;
    }, 2000);
    
    // Pause scanner while processing
    setScannerEnabled(false);
    setCurrentBarcode(barcode);
    
    console.log(`Scanned: ${barcode} (${format})`);
  }, []);

  /**
   * Handle manual barcode input
   */
  const handleManualInput = useCallback((barcode: string) => {
    setCurrentBarcode(barcode);
    // Switch to camera tab to show the action panel
    setInputMode('camera');
  }, []);

  /**
   * Handle scanner error
   */
  const handleScanError = useCallback((error: Error) => {
    console.error('Scanner error:', error);
  }, []);

  /**
   * Handle action completion
   * Records the action in history
   */
  const handleActionComplete = useCallback((result: ActionResult) => {
    // Add to scan history (Requirement 5.3)
    const record: ScanRecord = {
      id: generateId(),
      barcode: currentBarcode || '',
      itemName: '', // Will be filled by the panel
      action: result.action,
      result: result.success ? 'success' : 'failed',
      timestamp: new Date(),
      message: result.message,
    };
    
    setScanHistory(prev => [record, ...prev]);
  }, [currentBarcode]);

  /**
   * Handle rescan request (Requirement 5.1, 5.2)
   * Reactivates the camera for continuous scanning
   */
  const handleRescan = useCallback(() => {
    setCurrentBarcode(null);
    lastScannedRef.current = null;
    setScannerEnabled(true);
  }, []);

  /**
   * Clear scan history
   */
  const handleClearHistory = useCallback(() => {
    setScanHistory([]);
  }, []);

  /**
   * Go back to previous page
   */
  const handleBack = useCallback(() => {
    router.back();
  }, [router]);

  return (
    <div className="flex flex-col h-[calc(100vh-8rem)] max-w-2xl mx-auto">
      {/* Header */}
      <div className="flex items-center gap-3 mb-4">
        <Button variant="ghost" size="icon" onClick={handleBack}>
          <ArrowLeft className="h-5 w-5" />
        </Button>
        <h1 className="text-xl font-semibold">扫码操作</h1>
      </div>

      {/* Main Content */}
      <div className="flex-1 flex flex-col gap-4 overflow-hidden">
        {/* Scanner / Manual Input Tabs */}
        <Tabs
          value={inputMode}
          onValueChange={(v) => setInputMode(v as 'camera' | 'manual')}
          className="flex-shrink-0"
        >
          <TabsList className="grid w-full grid-cols-2">
            <TabsTrigger value="camera" className="flex items-center gap-2">
              <ScanLine className="h-4 w-4" />
              摄像头扫描
            </TabsTrigger>
            <TabsTrigger value="manual" className="flex items-center gap-2">
              <Keyboard className="h-4 w-4" />
              手动输入
            </TabsTrigger>
          </TabsList>

          <TabsContent value="camera" className="mt-4">
            {/* Barcode Scanner */}
            <BarcodeScanner
              onScan={handleScan}
              onError={handleScanError}
              enabled={scannerEnabled && inputMode === 'camera'}
              className="aspect-[4/3] max-h-[300px]"
            />
          </TabsContent>

          <TabsContent value="manual" className="mt-4">
            {/* Manual Input */}
            <ManualInput
              onSubmit={handleManualInput}
              autoFocus={inputMode === 'manual'}
              placeholder="输入条码号..."
            />
          </TabsContent>
        </Tabs>

        {/* Quick Action Panel */}
        <QuickActionPanel
          barcode={currentBarcode}
          onActionComplete={handleActionComplete}
          onRescan={handleRescan}
          className="flex-shrink-0"
        />

        {/* Scan History (Requirement 5.3, 5.4) */}
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
