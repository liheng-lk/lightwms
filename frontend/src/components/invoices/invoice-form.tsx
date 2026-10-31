'use client';

import { useEffect, useState, useRef } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { FileText, X, Upload } from 'lucide-react';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
  FormDescription,
} from '@/components/ui/form';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { useCreateInvoice, useRecognizeInvoice, useUpdateInvoice } from '@/lib/hooks/use-invoices';
import type { Invoice } from '@/lib/types';

// Accepted invoice file types - Requirements 23.2
const ACCEPTED_INVOICE_TYPES = ['application/pdf', 'image/jpeg', 'image/jpg', 'image/png'];
const ACCEPTED_INVOICE_EXTENSIONS = '.pdf,.jpg,.jpeg,.png';

// Predefined categories
const INVOICE_CATEGORIES = [
  '采购',
  '办公用品',
  '设备',
  '耗材',
  '服务',
  '维修',
  '其他',
];

// Form validation schema
const invoiceFormSchema = z.object({
  name: z.string().min(1, '请输入发票名称'),
  amount: z.number().min(0, '金额不能为负数'),
  category: z.string().min(1, '请选择类别'),
  custom_type: z.string().optional(),
  project: z.string().optional(),
});

type InvoiceFormData = z.infer<typeof invoiceFormSchema>;

interface InvoiceFormProps {
  invoice?: Invoice;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSuccess?: () => void;
}

export function InvoiceForm({ invoice, open, onOpenChange, onSuccess }: InvoiceFormProps) {
  const isEditing = !!invoice;
  const { mutate: createInvoice, isPending: isCreating } = useCreateInvoice();
  const { mutate: updateInvoice, isPending: isUpdating } = useUpdateInvoice();
  const recognizeInvoice = useRecognizeInvoice();
  
  // File state (only for create)
  const [invoiceFile, setInvoiceFile] = useState<File | null>(null);
  const [fileError, setFileError] = useState<string>('');
  const fileInputRef = useRef<HTMLInputElement>(null);
  
  const isPending = isCreating || isUpdating;

  const form = useForm<InvoiceFormData>({
    resolver: zodResolver(invoiceFormSchema),
    defaultValues: {
      name: '',
      amount: 0,
      category: '采购',
      custom_type: '',
      project: '',
    },
  });

  // Reset form when dialog opens/closes or invoice changes
  useEffect(() => {
    if (open) {
      setInvoiceFile(null);
      setFileError('');
      
      if (invoice) {
        form.reset({
          name: invoice.name,
          amount: invoice.amount,
          category: invoice.category,
          custom_type: invoice.custom_type || '',
          project: invoice.project || '',
        });
      } else {
        form.reset({
          name: '',
          amount: 0,
          category: '采购',
          custom_type: '',
          project: '',
        });
      }
    }
  }, [open, invoice, form]);

  // Handle file selection
  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    setFileError('');
    
    if (file) {
      if (!ACCEPTED_INVOICE_TYPES.includes(file.type)) {
        setFileError('请上传 PDF、JPG 或 PNG 格式的文件');
        return;
      }
      setInvoiceFile(file);
      if (file.type.startsWith('image/')) {
        recognizeInvoice.mutate(file, {
          onSuccess: (fields) => {
            if (fields.amount && !form.getValues('amount')) {
              form.setValue('amount', Number(fields.amount), { shouldValidate: true });
            }
            if (fields.name && !form.getValues('name')) {
              form.setValue('name', fields.name, { shouldValidate: true });
            }
          },
        });
      }
    }
  };

  const removeFile = () => {
    setInvoiceFile(null);
    setFileError('');
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  const onSubmit = (data: InvoiceFormData) => {
    if (isEditing && invoice) {
      // Update existing invoice
      updateInvoice(
        {
          id: invoice.id,
          data: {
            name: data.name,
            amount: data.amount,
            category: data.category,
            custom_type: data.custom_type || '',
            project: data.project || '',
          },
        },
        {
          onSuccess: () => {
            form.reset();
            onOpenChange(false);
            onSuccess?.();
          },
        }
      );
    } else {
      // Create new invoice - file is required
      if (!invoiceFile) {
        setFileError('请上传发票文件');
        return;
      }

      createInvoice(
        {
          name: data.name,
          amount: data.amount,
          category: data.category,
          custom_type: data.custom_type,
          project: data.project,
          file: invoiceFile,
        },
        {
          onSuccess: () => {
            form.reset();
            setInvoiceFile(null);
            onOpenChange(false);
            onSuccess?.();
          },
        }
      );
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[450px]">
        <DialogHeader>
          <DialogTitle>{isEditing ? '编辑发票' : '新增发票'}</DialogTitle>
        </DialogHeader>

        <Form {...form}>
          <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
            {/* 发票名称 */}
            <FormField
              control={form.control}
              name="name"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>发票名称 *</FormLabel>
                  <FormControl>
                    <Input placeholder="例如：办公电脑采购" {...field} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            {/* 金额 */}
            <FormField
              control={form.control}
              name="amount"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>金额 *</FormLabel>
                  <FormControl>
                    <Input
                      type="number"
                      step="0.01"
                      min="0"
                      placeholder="0.00"
                      {...field}
                      onChange={(e) => field.onChange(parseFloat(e.target.value) || 0)}
                    />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            {/* 类别 */}
            <FormField
              control={form.control}
              name="category"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>类别 *</FormLabel>
                  <Select value={field.value} onValueChange={field.onChange}>
                    <FormControl>
                      <SelectTrigger>
                        <SelectValue placeholder="选择类别" />
                      </SelectTrigger>
                    </FormControl>
                    <SelectContent>
                      {INVOICE_CATEGORIES.map((cat) => (
                        <SelectItem key={cat} value={cat}>
                          {cat}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  <FormMessage />
                </FormItem>
              )}
            />

            {/* 自定义类型 */}
            <FormField
              control={form.control}
              name="custom_type"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>自定义类型</FormLabel>
                  <FormControl>
                    <Input placeholder="可选，进一步分类" {...field} />
                  </FormControl>
                  <FormDescription>
                    用于更细致的分类，如"打印机耗材"
                  </FormDescription>
                  <FormMessage />
                </FormItem>
              )}
            />

            {/* 项目 */}
            <FormField
              control={form.control}
              name="project"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>项目</FormLabel>
                  <FormControl>
                    <Input placeholder="可选，关联的项目名称" {...field} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            {/* 文件上传 - 仅新增时显示 */}
            {!isEditing && (
              <div className="space-y-2">
                <FormLabel>发票文件 *</FormLabel>
                <FormDescription>
                  支持 PDF、JPG、PNG 格式
                </FormDescription>
                
                <input
                  ref={fileInputRef}
                  type="file"
                  accept={ACCEPTED_INVOICE_EXTENSIONS}
                  onChange={handleFileChange}
                  className="hidden"
                  id="invoice-file-input"
                />
                
                {invoiceFile ? (
                  <div className="flex items-center gap-2 p-3 bg-muted rounded-md">
                    <FileText className="h-4 w-4 text-muted-foreground" />
                    <span className="flex-1 text-sm truncate">{invoiceFile.name}</span>
                    <Button
                      type="button"
                      variant="ghost"
                      size="sm"
                      onClick={removeFile}
                      className="h-6 w-6 p-0"
                    >
                      <X className="h-4 w-4" />
                    </Button>
                  </div>
                ) : (
                  <Button
                    type="button"
                    variant="outline"
                    onClick={() => fileInputRef.current?.click()}
                    className="w-full"
                  >
                    <Upload className="h-4 w-4 mr-2" />
                    选择文件
                  </Button>
                )}
                
                {fileError && (
                  <p className="text-sm text-destructive">{fileError}</p>
                )}
              </div>
            )}

            {/* 编辑时显示当前文件信息 */}
            {isEditing && invoice?.original_filename && (
              <div className="space-y-2">
                <FormLabel>当前文件</FormLabel>
                <div className="flex items-center gap-2 p-3 bg-muted rounded-md">
                  <FileText className="h-4 w-4 text-muted-foreground" />
                  <span className="flex-1 text-sm truncate">{invoice.original_filename}</span>
                  {invoice.file && (
                    <Button
                      type="button"
                      variant="ghost"
                      size="sm"
                      asChild
                    >
                      <a href={`/api/media/${invoice.file.replace(/^\/?media\//, '')}`} target="_blank" rel="noopener noreferrer">
                        查看
                      </a>
                    </Button>
                  )}
                </div>
              </div>
            )}

            <DialogFooter>
              <Button
                type="button"
                variant="outline"
                onClick={() => onOpenChange(false)}
              >
                取消
              </Button>
              <Button type="submit" disabled={isPending}>
                {isPending ? '提交中...' : isEditing ? '保存' : '创建'}
              </Button>
            </DialogFooter>
          </form>
        </Form>
      </DialogContent>
    </Dialog>
  );
}
