'use client';

import { useState, useEffect, useRef } from 'react';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
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
import { ScrollArea } from '@/components/ui/scroll-area';
import { Printer, Download, Loader2 } from 'lucide-react';
import { useGenerateBarcodes } from '@/lib/hooks/use-items';
import type { Item } from '@/lib/types';
import type { GenerateBarcodeResponse } from '@/lib/api/items';

// Label size configurations - Requirements 25.3
const LABEL_SIZES = [
  { id: 'small', name: '30×20mm', width: 30, height: 20 },
  { id: 'medium', name: '40×30mm', width: 40, height: 30 },
  { id: 'large', name: '50×30mm', width: 50, height: 30 },
  { id: 'xlarge', name: '60×40mm', width: 60, height: 40 },
] as const;

// Columns per page options - Requirements 25.5
const COLUMNS_OPTIONS = [2, 3, 4, 5];

// Storage key for user preferences - Requirements 25.7
const PRINT_CONFIG_STORAGE_KEY = 'barcode-print-config';

interface PrintConfig {
  labelSize: string;
  columns: number;
}

interface BarcodePrintDialogProps {
  items: Item[];
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

interface BarcodeData {
  itemId: number;
  itemName: string;
  itemSku: string;
  barcode: string;
  barcodeImage: string;
}

export function BarcodePrintDialog({ items, open, onOpenChange }: BarcodePrintDialogProps) {
  const printRef = useRef<HTMLDivElement>(null);
  const generateBarcodesMutation = useGenerateBarcodes();
  
  // Load saved config from localStorage - Requirements 25.7
  const [config, setConfig] = useState<PrintConfig>(() => {
    if (typeof window !== 'undefined') {
      const saved = localStorage.getItem(PRINT_CONFIG_STORAGE_KEY);
      if (saved) {
        try {
          return JSON.parse(saved);
        } catch {
          // Ignore parse errors
        }
      }
    }
    return { labelSize: 'medium', columns: 3 };
  });
  
  const [barcodeData, setBarcodeData] = useState<BarcodeData[]>([]);
  const [isGenerating, setIsGenerating] = useState(false);
  
  // Create stable item IDs string for dependency
  const itemIdsKey = items.map(item => item.id).sort().join(',');

  // Save config to localStorage when it changes - Requirements 25.7
  useEffect(() => {
    if (typeof window !== 'undefined') {
      localStorage.setItem(PRINT_CONFIG_STORAGE_KEY, JSON.stringify(config));
    }
  }, [config]);

  // Generate barcodes when dialog opens
  useEffect(() => {
    if (open && items.length > 0) {
      setIsGenerating(true);
      setBarcodeData([]);
      
      // Generate barcodes for all selected items
      const itemIds = items.map(item => item.id);
      generateBarcodesMutation.mutate(itemIds, {
        onSuccess: (results: GenerateBarcodeResponse[]) => {
          const data: BarcodeData[] = results.map((result: GenerateBarcodeResponse, index: number) => ({
            itemId: items[index].id,
            itemName: items[index].name,
            itemSku: items[index].sku,
            barcode: result.barcode,
            barcodeImage: result.barcode_image || result.label_png_base64 || '',
          }));
          setBarcodeData(data);
          setIsGenerating(false);
        },
        onError: () => {
          setIsGenerating(false);
        },
      });
    } else if (!open) {
      // Reset state when dialog closes
      setBarcodeData([]);
      setIsGenerating(false);
    }
  }, [open, itemIdsKey]); // eslint-disable-line react-hooks/exhaustive-deps

  const selectedLabelSize = LABEL_SIZES.find(s => s.id === config.labelSize) || LABEL_SIZES[1];

  // Handle print - Requirements 25.6
  const handlePrint = () => {
    if (!printRef.current) return;
    
    const printWindow = window.open('', '_blank');
    if (!printWindow) return;

    const labelWidth = selectedLabelSize.width;
    const labelHeight = selectedLabelSize.height;
    const columns = config.columns;
    const imageCount = barcodeData.length;

    printWindow.document.write(`
      <!DOCTYPE html>
      <html>
        <head>
          <title>打印条码标签</title>
          <style>
            @page {
              size: A4;
              margin: 10mm;
            }
            * {
              box-sizing: border-box;
              margin: 0;
              padding: 0;
            }
            body {
              font-family: Arial, sans-serif;
            }
            .print-container {
              display: grid;
              grid-template-columns: repeat(${columns}, ${labelWidth}mm);
              gap: 2mm;
              justify-content: start;
            }
            .label {
              width: ${labelWidth}mm;
              height: ${labelHeight}mm;
              border: 0.5px dashed #ccc;
              display: flex;
              flex-direction: column;
              align-items: center;
              justify-content: center;
              padding: 1mm;
              page-break-inside: avoid;
            }
            .barcode-image {
              max-width: ${labelWidth - 4}mm;
              max-height: ${labelHeight - 10}mm;
              object-fit: contain;
            }
            .item-name {
              font-size: 7pt;
              text-align: center;
              margin-top: 1mm;
              max-width: ${labelWidth - 2}mm;
              overflow: hidden;
              text-overflow: ellipsis;
              white-space: nowrap;
            }
            @media print {
              .label {
                border: none;
              }
            }
          </style>
        </head>
        <body>
          <div class="print-container">
            ${barcodeData.map(data => `
              <div class="label">
                <img src="data:image/png;base64,${data.barcodeImage}" class="barcode-image" alt="${data.barcode}" />
                <div class="item-name">${data.itemName}</div>
              </div>
            `).join('')}
          </div>
          <script>
            // Wait for all images to load before printing
            var images = document.querySelectorAll('.barcode-image');
            var loadedCount = 0;
            var totalImages = ${imageCount};
            
            function checkAllLoaded() {
              loadedCount++;
              if (loadedCount >= totalImages) {
                setTimeout(function() {
                  window.print();
                  window.onafterprint = function() {
                    window.close();
                  };
                }, 100);
              }
            }
            
            if (totalImages === 0) {
              window.print();
            } else {
              images.forEach(function(img) {
                if (img.complete) {
                  checkAllLoaded();
                } else {
                  img.onload = checkAllLoaded;
                  img.onerror = checkAllLoaded;
                }
              });
            }
          </script>
        </body>
      </html>
    `);
    printWindow.document.close();
  };

  // Handle PDF export - Requirements 25.6
  const handleExportPdf = () => {
    if (!printRef.current) return;
    
    const labelWidth = selectedLabelSize.width;
    const labelHeight = selectedLabelSize.height;
    const columns = config.columns;

    // Create a new window with print-ready content
    const pdfWindow = window.open('', '_blank');
    if (!pdfWindow) return;

    pdfWindow.document.write(`
      <!DOCTYPE html>
      <html>
        <head>
          <title>条码标签 - PDF导出</title>
          <style>
            @page {
              size: A4;
              margin: 10mm;
            }
            * {
              box-sizing: border-box;
              margin: 0;
              padding: 0;
            }
            body {
              font-family: Arial, sans-serif;
            }
            .print-container {
              display: grid;
              grid-template-columns: repeat(${columns}, ${labelWidth}mm);
              gap: 2mm;
              justify-content: start;
            }
            .label {
              width: ${labelWidth}mm;
              height: ${labelHeight}mm;
              border: 0.5px dashed #ccc;
              display: flex;
              flex-direction: column;
              align-items: center;
              justify-content: center;
              padding: 1mm;
              page-break-inside: avoid;
            }
            .barcode-image {
              max-width: ${labelWidth - 4}mm;
              max-height: ${labelHeight - 10}mm;
              object-fit: contain;
            }
            .item-name {
              font-size: 7pt;
              text-align: center;
              margin-top: 1mm;
              max-width: ${labelWidth - 2}mm;
              overflow: hidden;
              text-overflow: ellipsis;
              white-space: nowrap;
            }
            .instructions {
              margin-bottom: 10mm;
              padding: 5mm;
              background: #f5f5f5;
              border-radius: 2mm;
            }
            .instructions h2 {
              font-size: 12pt;
              margin-bottom: 3mm;
            }
            .instructions p {
              font-size: 9pt;
              color: #666;
            }
          </style>
        </head>
        <body>
          <div class="instructions">
            <h2>条码标签导出</h2>
            <p>请使用浏览器的「打印」功能（Ctrl+P 或 Cmd+P）将此页面保存为 PDF 文件。</p>
            <p>标签规格：${selectedLabelSize.name}，每行 ${columns} 个</p>
          </div>
          <div class="print-container">
            ${barcodeData.map(data => `
              <div class="label">
                <img src="data:image/png;base64,${data.barcodeImage}" class="barcode-image" alt="${data.barcode}" />
                <div class="item-name">${data.itemName}</div>
              </div>
            `).join('')}
          </div>
        </body>
      </html>
    `);
    pdfWindow.document.close();
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-4xl max-h-[90vh] flex flex-col">
        <DialogHeader>
          <DialogTitle>批量打印条码</DialogTitle>
        </DialogHeader>
        
        <div className="flex-1 overflow-hidden flex flex-col gap-4">
          {/* Configuration section - Requirements 25.3, 25.5 */}
          <div className="flex flex-wrap gap-4 items-end border-b pb-4">
            <div className="space-y-2">
              <Label>标签规格</Label>
              <Select
                value={config.labelSize}
                onValueChange={(value) => setConfig(prev => ({ ...prev, labelSize: value }))}
              >
                <SelectTrigger className="w-[140px]">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {LABEL_SIZES.map((size) => (
                    <SelectItem key={size.id} value={size.id}>
                      {size.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            
            <div className="space-y-2">
              <Label>每行数量</Label>
              <Select
                value={String(config.columns)}
                onValueChange={(value) => setConfig(prev => ({ ...prev, columns: Number(value) }))}
              >
                <SelectTrigger className="w-[100px]">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {COLUMNS_OPTIONS.map((cols) => (
                    <SelectItem key={cols} value={String(cols)}>
                      {cols} 个
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            
            <div className="text-sm text-muted-foreground">
              已选择 {items.length} 个物品
            </div>
          </div>
          
          {/* Preview section - Requirements 25.2, 25.4 */}
          <div className="flex-1 overflow-hidden">
            <Label className="mb-2 block">预览</Label>
            <ScrollArea className="h-[400px] border rounded-lg p-4 bg-white">
              {isGenerating ? (
                <div className="flex flex-col items-center justify-center h-full gap-2">
                  <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
                  <p className="text-sm text-muted-foreground">正在生成条码...</p>
                </div>
              ) : barcodeData.length === 0 ? (
                <div className="flex items-center justify-center h-full text-muted-foreground">
                  暂无条码数据
                </div>
              ) : (
                <div 
                  ref={printRef}
                  className="grid gap-2"
                  style={{ 
                    gridTemplateColumns: `repeat(${config.columns}, ${selectedLabelSize.width * 3}px)` 
                  }}
                >
                  {barcodeData.map((data) => (
                    <div
                      key={data.itemId}
                      className="border border-dashed border-gray-300 rounded flex flex-col items-center justify-center p-2"
                      style={{
                        width: `${selectedLabelSize.width * 3}px`,
                        height: `${selectedLabelSize.height * 3}px`,
                      }}
                    >
                      {/* eslint-disable-next-line @next/next/no-img-element */}
                      <img
                        src={`data:image/png;base64,${data.barcodeImage}`}
                        alt={data.barcode}
                        className="max-w-full max-h-[60%] object-contain"
                      />
                      <div className="text-xs text-center mt-1 truncate w-full">
                        {data.itemName}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </ScrollArea>
          </div>
        </div>
        
        <DialogFooter className="flex-row justify-end gap-2">
          <Button variant="ghost" onClick={() => onOpenChange(false)}>
            取消
          </Button>
          <Button 
            variant="outline" 
            onClick={handleExportPdf}
            disabled={isGenerating || barcodeData.length === 0}
          >
            <Download className="h-4 w-4 mr-2" />
            导出 PDF
          </Button>
          <Button 
            onClick={handlePrint}
            disabled={isGenerating || barcodeData.length === 0}
          >
            <Printer className="h-4 w-4 mr-2" />
            打印
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
