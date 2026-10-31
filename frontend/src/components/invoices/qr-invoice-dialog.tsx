'use client';

import { useEffect, useRef, useState } from 'react';
import { QrCode } from 'lucide-react';
import { BrowserQRCodeReader } from '@zxing/browser';
import { toast } from 'sonner';
import { Button } from '@/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { fetchTaxInvoicePdf, useCreateInvoice, useRecognizeInvoice } from '@/lib/hooks/use-invoices';

const CATEGORIES = ['采购', '办公用品', '设备', '耗材', '服务', '维修', '其他'];

interface QrInvoiceDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onImported?: () => void;
}

function invoiceNumberFrom(url: string): string {
  return url.match(/(\d{20})/)?.[1] || '';
}

export function QrInvoiceDialog({ open, onOpenChange, onImported }: QrInvoiceDialogProps) {
  const createInvoice = useCreateInvoice();
  const recognizeInvoice = useRecognizeInvoice();
  const videoRef = useRef<HTMLVideoElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const stopCamera = useRef<(() => void) | null>(null);
  const cameraHandled = useRef(false);
  const amountTouched = useRef(false);
  const [pdfFile, setPdfFile] = useState<File | null>(null);
  const [downloading, setDownloading] = useState(false);
  const [qrUrl, setQrUrl] = useState('');
  const [name, setName] = useState('');
  const [amount, setAmount] = useState('');
  const [category, setCategory] = useState('采购');
  const [cameraOn, setCameraOn] = useState(false);
  const [recognizing, setRecognizing] = useState(false);

  const reset = () => {
    stopCamera.current?.();
    stopCamera.current = null;
    cameraHandled.current = false;
    amountTouched.current = false;
    setCameraOn(false);
    setPdfFile(null);
    setDownloading(false);
    setQrUrl('');
    setName('');
    setAmount('');
    setCategory('采购');
    setRecognizing(false);
    if (fileInputRef.current) fileInputRef.current.value = '';
  };

  useEffect(() => {
    if (!open) reset();
    return () => stopCamera.current?.();
    // reset is local and only needed when the dialog closes
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open]);

  const applyResult = (text: string) => {
    const url = text.trim();
    if (!/^https:\/\//i.test(url)) {
      toast.error('二维码里不是发票下载链接');
      return;
    }
    setQrUrl(url);
    const number = invoiceNumberFrom(url);
    setName(number ? `数电发票${number}` : '电子发票');
    void downloadOfficialPdf(url);
  };

  const downloadOfficialPdf = async (url: string) => {
    setDownloading(true);
    setPdfFile(null);
    try {
      const pdf = await fetchTaxInvoicePdf(url);
      if (!pdf.size || (pdf.type && !pdf.type.includes('pdf') && !pdf.name.toLowerCase().endsWith('.pdf'))) {
        throw new Error('税务网站没有返回 PDF');
      }
      setPdfFile(pdf);
      await fillFromImage(pdf);
    } catch (error) {
      setPdfFile(null);
      toast.error(error instanceof Error ? error.message : '没有下载到发票 PDF，请手动上传 PDF');
    } finally {
      setDownloading(false);
    }
  };

  const fillFromImage = async (selected: File) => {
    setRecognizing(true);
    try {
      const fields = await recognizeInvoice.mutateAsync(selected);
      if (fields.amount && !amountTouched.current) setAmount(fields.amount);
      if (fields.name) setName((current) => current.startsWith('数电发票') || !current ? fields.name : current);
    } catch {
      // The picture can still be saved when recognition fails.
    } finally {
      setRecognizing(false);
    }
  };

  const decodeFile = async (selected: File) => {
    const imageUrl = URL.createObjectURL(selected);
    try {
      const image = new Image();
      image.src = imageUrl;
      await image.decode();
      const result = await new BrowserQRCodeReader().decodeFromImageElement(image);
      applyResult(result.getText());
    } catch {
      toast.error('没有识别到发票二维码');
    } finally {
      URL.revokeObjectURL(imageUrl);
    }
  };

  const startCamera = async () => {
    if (!videoRef.current) return;
    try {
      cameraHandled.current = false;
      const controls = await new BrowserQRCodeReader().decodeFromVideoDevice(undefined, videoRef.current, (result) => {
        if (!result || cameraHandled.current) return;
        cameraHandled.current = true;
        applyResult(result.getText());
        stopCamera.current?.();
        stopCamera.current = null;
        setCameraOn(false);
      });
      stopCamera.current = () => controls.stop();
      setCameraOn(true);
    } catch {
      toast.error('无法打开摄像头。手机如果用的是 http 地址，请改为上传二维码图片。');
    }
  };

  const save = async () => {
    const raw = amount.trim();
    const value = Number(raw);
    if (!pdfFile) {
      toast.error(downloading ? '正在下载发票 PDF' : '请先下载到正式 PDF，不能保存二维码图片');
      return;
    }
    if (!raw || !Number.isFinite(value) || value < 0) {
      toast.error('请填写发票金额');
      return;
    }
    try {
      await createInvoice.mutateAsync({
        name: name.trim() || pdfFile.name.replace(/\.pdf$/i, '') || '电子发票',
        amount: value,
        category,
        custom_type: '电子发票',
        project: qrUrl.slice(0, 200),
        file: pdfFile,
      });
      toast.success('已按二维码登记发票');
      onOpenChange(false);
      onImported?.();
    } catch (error) {
      toast.error(error instanceof Error ? error.message : '登记失败');
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-h-[85vh] overflow-y-auto sm:max-w-[520px]">
        <DialogHeader>
          <DialogTitle>扫描二维码</DialogTitle>
          <DialogDescription>
            识别二维码后只下载并保存税务网站的 PDF。下载不到 PDF 时不会登记二维码图片。
          </DialogDescription>
        </DialogHeader>
        <Input
          ref={fileInputRef}
          type="file"
          accept="image/png,image/jpeg,image/jpg"
          onChange={(event) => {
            const selected = event.target.files?.[0];
            if (selected) void decodeFile(selected);
          }}
        />
        <div className="space-y-2">
          <video ref={videoRef} className={cameraOn ? 'w-full rounded-md bg-black' : 'hidden'} muted playsInline />
          <Button type="button" variant="outline" onClick={startCamera} disabled={cameraOn}>
            <QrCode className="mr-2 h-4 w-4" />
            {cameraOn ? '正在扫描…' : '打开摄像头'}
          </Button>
        </div>
        {(qrUrl || downloading || pdfFile) && (
          <div className="space-y-2 text-sm">
            {downloading && <p className="text-xs text-muted-foreground">正在下载正式发票 PDF…</p>}
            {pdfFile && <p className="text-xs text-muted-foreground">将保存文件：{pdfFile.name}</p>}
            {recognizing && <p className="text-xs text-muted-foreground">正在识别金额…</p>}
            <Input value={name} onChange={(event) => setName(event.target.value)} placeholder="发票名称" />
            <div className="grid grid-cols-2 gap-2">
              <Input
                inputMode="decimal"
                value={amount}
                onChange={(event) => {
                  amountTouched.current = true;
                  setAmount(event.target.value);
                }}
                placeholder="金额"
              />
              <Select value={category} onValueChange={setCategory}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  {CATEGORIES.map((item) => <SelectItem key={item} value={item}>{item}</SelectItem>)}
                </SelectContent>
              </Select>
            </div>
            <Button onClick={save} disabled={createInvoice.isPending || downloading || !pdfFile}>
              {createInvoice.isPending ? '正在登记…' : '登记为发票'}
            </Button>
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}
