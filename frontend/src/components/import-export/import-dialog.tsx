'use client';

import { useState, useCallback } from 'react';
import { Upload, FileSpreadsheet, AlertCircle, CheckCircle2, X } from 'lucide-react';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { ScrollArea } from '@/components/ui/scroll-area';
import { useImportItems, useDownloadTemplate, type ImportResult, type ImportError } from '@/lib/hooks/use-import-export';

interface ImportDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSuccess?: () => void;
}

export function ImportDialog({ open, onOpenChange, onSuccess }: ImportDialogProps) {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [importResult, setImportResult] = useState<ImportResult | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  
  const importMutation = useImportItems();
  const downloadTemplateMutation = useDownloadTemplate();

  const resetState = useCallback(() => {
    setSelectedFile(null);
    setImportResult(null);
  }, []);

  const handleClose = useCallback((open: boolean) => {
    if (!open) {
      resetState();
    }
    onOpenChange(open);
  }, [onOpenChange, resetState]);

  const handleFileSelect = useCallback((file: File) => {
    // Validate file type
    const validTypes = [
      'text/csv',
      'application/vnd.ms-excel',
      'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    ];
    const validExtensions = ['.csv', '.xls', '.xlsx'];
    
    const hasValidType = validTypes.includes(file.type);
    const hasValidExtension = validExtensions.some(ext => 
      file.name.toLowerCase().endsWith(ext)
    );
    
    if (!hasValidType && !hasValidExtension) {
      return;
    }
    
    setSelectedFile(file);
    setImportResult(null);
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    
    const file = e.dataTransfer.files[0];
    if (file) {
      handleFileSelect(file);
    }
  }, [handleFileSelect]);

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  }, []);

  const handleFileInputChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      handleFileSelect(file);
    }
    // Reset input value to allow selecting the same file again
    e.target.value = '';
  }, [handleFileSelect]);

  const handleImport = useCallback(async () => {
    if (!selectedFile) return;
    
    try {
      const result = await importMutation.mutateAsync(selectedFile);
      setImportResult(result);
      
      if (result.errors.length === 0) {
        onSuccess?.();
      }
    } catch {
      // Error handled by mutation
    }
  }, [selectedFile, importMutation, onSuccess]);

  const handleDownloadTemplate = useCallback(() => {
    downloadTemplateMutation.mutate();
  }, [downloadTemplateMutation]);

  const handleRemoveFile = useCallback(() => {
    setSelectedFile(null);
    setImportResult(null);
  }, []);

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>导入物品</DialogTitle>
          <DialogDescription>
            上传 CSV 或 Excel 文件批量导入物品数据
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
          {/* File upload area */}
          {!importResult && (
            <div
              className={`
                border-2 border-dashed rounded-lg p-6 text-center transition-colors
                ${isDragging ? 'border-primary bg-primary/5' : 'border-muted-foreground/25'}
                ${selectedFile ? 'bg-muted/50' : 'hover:border-primary/50'}
              `}
              onDrop={handleDrop}
              onDragOver={handleDragOver}
              onDragLeave={handleDragLeave}
            >
              {selectedFile ? (
                <div className="flex items-center justify-center gap-3">
                  <FileSpreadsheet className="h-8 w-8 text-green-600" />
                  <div className="text-left">
                    <p className="font-medium">{selectedFile.name}</p>
                    <p className="text-sm text-muted-foreground">
                      {(selectedFile.size / 1024).toFixed(1)} KB
                    </p>
                  </div>
                  <Button
                    variant="ghost"
                    size="icon"
                    className="ml-2"
                    onClick={handleRemoveFile}
                  >
                    <X className="h-4 w-4" />
                  </Button>
                </div>
              ) : (
                <>
                  <Upload className="h-10 w-10 mx-auto text-muted-foreground mb-3" />
                  <p className="text-sm text-muted-foreground mb-2">
                    拖拽文件到此处，或点击选择文件
                  </p>
                  <p className="text-xs text-muted-foreground">
                    支持 .csv, .xls, .xlsx 格式
                  </p>
                  <input
                    type="file"
                    accept=".csv,.xls,.xlsx"
                    className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
                    onChange={handleFileInputChange}
                  />
                </>
              )}
            </div>
          )}

          {/* Import result */}
          {importResult && (
            <ImportResultDisplay result={importResult} />
          )}

          {/* Download template link */}
          {!importResult && (
            <div className="text-center">
              <Button
                variant="link"
                size="sm"
                onClick={handleDownloadTemplate}
                disabled={downloadTemplateMutation.isPending}
              >
                <FileSpreadsheet className="h-4 w-4 mr-1" />
                下载导入模板
              </Button>
            </div>
          )}
        </div>

        <DialogFooter>
          {importResult ? (
            <Button onClick={() => handleClose(false)}>
              关闭
            </Button>
          ) : (
            <>
              <Button variant="outline" onClick={() => handleClose(false)}>
                取消
              </Button>
              <Button
                onClick={handleImport}
                disabled={!selectedFile || importMutation.isPending}
              >
                {importMutation.isPending ? '导入中...' : '开始导入'}
              </Button>
            </>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

// Import result display component
function ImportResultDisplay({ result }: { result: ImportResult }) {
  const hasErrors = result.errors.length > 0;
  
  return (
    <div className="space-y-4">
      {/* Summary */}
      <div className={`
        flex items-center gap-3 p-4 rounded-lg
        ${hasErrors ? 'bg-yellow-50 border border-yellow-200' : 'bg-green-50 border border-green-200'}
      `}>
        {hasErrors ? (
          <AlertCircle className="h-5 w-5 text-yellow-600 shrink-0" />
        ) : (
          <CheckCircle2 className="h-5 w-5 text-green-600 shrink-0" />
        )}
        <div>
          <p className={`font-medium ${hasErrors ? 'text-yellow-800' : 'text-green-800'}`}>
            {hasErrors ? '导入完成（部分失败）' : '导入成功'}
          </p>
          <p className="text-sm text-muted-foreground">
            共处理 {result.total} 条，新增 {result.created} 条，更新 {result.updated} 条
            {hasErrors && `，失败 ${result.errors.length} 条`}
          </p>
        </div>
      </div>

      {/* Error list */}
      {hasErrors && (
        <div className="space-y-2">
          <p className="text-sm font-medium text-destructive">错误详情：</p>
          <ScrollArea className="h-[200px] rounded-md border p-3">
            <div className="space-y-2">
              {result.errors.map((error, index) => (
                <ErrorRow key={index} error={error} />
              ))}
            </div>
          </ScrollArea>
        </div>
      )}
    </div>
  );
}

// Error row component
function ErrorRow({ error }: { error: ImportError }) {
  return (
    <div className="flex items-start gap-2 text-sm">
      <span className="text-muted-foreground shrink-0">第 {error.row} 行</span>
      {error.field && (
        <span className="text-muted-foreground shrink-0">[{error.field}]</span>
      )}
      <span className="text-destructive">{error.message}</span>
    </div>
  );
}
