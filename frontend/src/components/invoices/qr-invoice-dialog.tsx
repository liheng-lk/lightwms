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
import { useCreateInvoice, useRecognizeInvoice } from '@/lib/hooks/use-invoices';

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
  const [file, setFile] = useState<File | null>(null);
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
    setFile(null);
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

  const captureFrame = (): File | null => {
    const video = videoRef.current;
    if (!video || !video.videoWidth) return null;
    const canvas = document.createElement('canvas');
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    const context = canvas.getContext('2d');
    if (!context) return null;
    context.drawImage(video, 0, 0);
    const dataUrl = canvas.toDataURL('image/jpeg', 0.92);
    const bytes = Uint8Array.from(atob(dataUrl.split(',')[1] || ''), (char) => char.charCodeAt(0));
    return new File([bytes], 'invoice-qr.jpg', { type: 'image/jpeg' });
  };

  const applyResult = (text: string, source: File | null) => {
    const url = text.trim();
    if (source) setFile(source);
    if (!/^https:\/\//i.test(url)) {
      toast.error('二维码里不是发票下载链接，改为识别发票内容');
      if (source) void fillFromImage(source);
      return;
    }
    const number = invoiceNumberFrom(url);
    setQrUrl(url);
    setName(number ? `数电发票${number}` : '二维码发票');
    if (source) void fillFromImage(source);
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
      applyResult(result.getText(), selected);
    } catch {
      setFile(selected);
      setQrUrl('');
      toast.message('没有识别到二维码，改为识别发票内容');
      void fillFromImage(selected);
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
        applyResult(result.getText(), captureFrame());
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
    if (!file) {
      toast.error('请先上传或拍下包含二维码的图片');
      return;
    }
    if (!raw || !Number.isFinite(value) || value < 0) {
      toast.error('请填写发票金额');
      return;
    }
    try {
      await createInvoice.mutateAsync({
        name: name.trim() || (qrUrl ? '二维码发票' : file.name.replace(/\.[^.]+$/, '') || '发票'),
        amount: value,
        category,
        custom_type: qrUrl ? '二维码发票' : '',
        project: qrUrl.slice(0, 200),
        file,
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
            上传发票图片，或打开摄像头扫描二维码。识别到金额会自动填上；没有二维码也可以按发票内容登记。
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
        {(qrUrl || file) && (
          <div className="space-y-2 text-sm">
            {qrUrl && (
              <a href={qrUrl} target="_blank" rel="noreferrer" className="break-all text-primary underline">
                {qrUrl}
              </a>
            )}
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
            <Button onClick={save} disabled={createInvoice.isPending}>
              {createInvoice.isPending ? '正在登记…' : '登记为发票'}
            </Button>
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}
