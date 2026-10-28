'use client';

import { useState, useEffect } from 'react';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Download, Printer, Loader2 } from 'lucide-react';
import { useGenerateBarcode } from '@/lib/hooks/use-items';
import type { GenerateBarcodeResponse } from '@/lib/api/items';
import type { Item } from '@/lib/types';
import { escapeHtml } from '@/lib/html';

interface BarcodeModalProps {
  item: Item;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSuccess?: () => void;
}

export function BarcodeModal({ item, open, onOpenChange, onSuccess }: BarcodeModalProps) {
  const { mutate, isPending, reset: resetMutation } = useGenerateBarcode();
  const [barcodeData, setBarcodeData] = useState<GenerateBarcodeResponse | null>(null);

  // Get barcode image from either field name (backend returns label_png_base64, normalized to barcode_image)
  const getBarcodeImage = () => {
    return barcodeData?.barcode_image || barcodeData?.label_png_base64;
  };

  // Generate barcode when modal opens
  useEffect(() => {
    if (open && !barcodeData && !isPending) {
      console.log('BarcodeModal: Generating barcode for item', item.id);
      mutate(item.id, {
        onSuccess: (response) => {
          console.log('BarcodeModal: Barcode generated', response);
          setBarcodeData(response);
          onSuccess?.();
        },
        onError: (error) => {
          console.error('BarcodeModal: Error generating barcode', error);
        },
      });
    }
  }, [open, item.id]);

  // Reset state when modal closes
  const handleClose = () => {
    setBarcodeData(null);
    resetMutation();
    onOpenChange(false);
  };

  // Download barcode image - Requirements 11.2
  const handleDownload = () => {
    const barcodeImage = getBarcodeImage();
    if (!barcodeImage) return;
    
    const link = document.createElement('a');
    link.href = `data:image/png;base64,${escapeHtml(barcodeImage)}`;
    link.download = `barcode-${escapeHtml(item.sku)}-${escapeHtml(barcodeData?.barcode)}.png`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  // Print barcode - Requirements 11.3
  const handlePrint = () => {
    const barcodeImage = getBarcodeImage();
    if (!barcodeImage) return;
    
    const printWindow = window.open('', '_blank');
    if (printWindow) {
      printWindow.document.write(`
        <!DOCTYPE html>
        <html>
          <head>
            <title>打印条码 - ${escapeHtml(item.sku)}</title>
            <style>
              body {
                font-family: Arial, sans-serif;
                text-align: center;
                padding: 20px;
                margin: 0;
              }
              .container {
                display: inline-block;
                padding: 20px;
                border: 1px solid #ddd;
              }
              .barcode-image {
                max-width: 300px;
                height: auto;
              }
              .item-name {
                font-size: 14px;
                margin-top: 10px;
                color: #333;
              }
              .item-sku {
                font-size: 12px;
                color: #666;
                margin-top: 5px;
              }
              .barcode-text {
                font-size: 16px;
                font-weight: bold;
                margin-top: 10px;
                font-family: monospace;
              }
              @media print {
                body { padding: 0; }
                .container { border: none; }
              }
            </style>
          </head>
          <body>
            <div class="container">
              <img src="data:image/png;base64,${escapeHtml(barcodeImage)}" class="barcode-image" alt="条码" />
              <div class="barcode-text">${escapeHtml(barcodeData?.barcode)}</div>
              <div class="item-name">${escapeHtml(item.name)}</div>
              <div class="item-sku">SKU: ${escapeHtml(item.sku)}</div>
            </div>
            <script>
              window.onload = function() {
                window.print();
                window.onafterprint = function() {
                  window.close();
                };
              };
            </script>
          </body>
        </html>
      `);
      printWindow.document.close();
    }
  };

  return (
    <Dialog open={open} onOpenChange={(newOpen) => !newOpen && handleClose()}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>生成条码</DialogTitle>
        </DialogHeader>
        
        <div className="flex flex-col items-center space-y-4 py-4">
          <div className="text-sm text-muted-foreground">
            物品：{item.name} ({item.sku})
          </div>
          
          {isPending && (
            <div className="flex flex-col items-center gap-2 py-8">
              <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
              <p className="text-sm text-muted-foreground">正在生成条码...</p>
            </div>
          )}
          
          {!isPending && barcodeData && getBarcodeImage() && (
            <div className="flex flex-col items-center gap-4">
              <div className="border rounded-lg p-4 bg-white">
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img
                  src={`data:image/png;base64,${getBarcodeImage()}`}
                  alt={`条码: ${barcodeData.barcode}`}
                  className="max-w-full h-auto"
                />
              </div>
              <p className="font-mono text-lg font-semibold">{barcodeData.barcode}</p>
            </div>
          )}
          
          {!isPending && barcodeData && !getBarcodeImage() && (
            <div className="text-sm text-destructive py-4">
              条码生成失败，请重试
            </div>
          )}
          
          {!isPending && !barcodeData && (
            <div className="text-sm text-muted-foreground py-4">
              点击下方按钮生成条码
            </div>
          )}
        </div>
        
        <DialogFooter className="flex-row justify-center gap-2 sm:justify-center">
          {barcodeData && getBarcodeImage() && (
            <>
              <Button variant="outline" onClick={handleDownload}>
                <Download className="h-4 w-4 mr-2" />
                下载
              </Button>
              <Button onClick={handlePrint}>
                <Printer className="h-4 w-4 mr-2" />
                打印
              </Button>
            </>
          )}
          <Button variant="ghost" onClick={handleClose}>
            关闭
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
