'use client';

import { useEffect, useState, useRef } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { FileText, X, Upload, Trash2 } from 'lucide-react';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from '@/components/ui/dialog';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from '@/components/ui/alert-dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
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
import { TreeSelect } from './tree-select';
import { useCategoryTree, useLocationTree } from '@/lib/hooks/use-trees';
import { useCreateItem, useUpdateItem, useDeleteItem } from '@/lib/hooks/use-items';
import { useCreateInvoice } from '@/lib/hooks/use-invoices';
import type { Item, ItemType } from '@/lib/types';

// Accepted invoice file types - Requirements 23.2
const ACCEPTED_INVOICE_TYPES = ['application/pdf', 'image/jpeg', 'image/jpg', 'image/png'];
const ACCEPTED_INVOICE_EXTENSIONS = '.pdf,.jpg,.jpeg,.png';

// Form validation schema
const itemFormSchema = z.object({
  name: z.string().min(1, '请输入物品名称'),
  sku: z.string().min(1, '请输入 SKU'),
  barcode: z.string().optional(),
  category: z.number().optional().nullable(),
  location: z.number({ error: '请选择库位' }),
  type: z.enum(['reusable', 'consumable'], { error: '请选择物品类型' }),
  quantity: z.number().min(0, '数量不能为负数').optional().nullable(),
  unit: z.string().optional(),
  description: z.string().optional(),
}).refine(
  (data) => {
    // consumable type requires quantity
    if (data.type === 'consumable' && (data.quantity === undefined || data.quantity === null)) {
      return false;
    }
    return true;
  },
  {
    message: '消耗品必须填写数量',
    path: ['quantity'],
  }
);

type ItemFormData = z.infer<typeof itemFormSchema>;

interface ItemFormProps {
  item?: Item;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSuccess?: () => void;
}

export function ItemForm({ item, open, onOpenChange, onSuccess }: ItemFormProps) {
  const isEditing = !!item;
  const { data: categories, isLoading: categoriesLoading } = useCategoryTree();
  const { data: locations, isLoading: locationsLoading } = useLocationTree();
  const { mutate: createItem, isPending: isCreating } = useCreateItem();
  const { mutate: updateItem, isPending: isUpdating } = useUpdateItem();
  const { mutate: deleteItem, isPending: isDeleting } = useDeleteItem();
  const { mutate: createInvoice, isPending: isCreatingInvoice } = useCreateInvoice();
  
  // Invoice file state - Requirements 23.1, 23.2
  const [invoiceFile, setInvoiceFile] = useState<File | null>(null);
  const [invoiceAmount, setInvoiceAmount] = useState<string>('');
  const [invoiceCategory, setInvoiceCategory] = useState<string>('采购');
  const fileInputRef = useRef<HTMLInputElement>(null);
  
  const isPending = isCreating || isUpdating || isCreatingInvoice || isDeleting;

  // Handle delete item
  const handleDelete = () => {
    if (!item) return;
    deleteItem(item.id, {
      onSuccess: () => {
        onOpenChange(false);
        onSuccess?.();
      },
    });
  };

  const form = useForm<ItemFormData>({
    resolver: zodResolver(itemFormSchema),
    defaultValues: {
      name: '',
      sku: '',
      barcode: '',
      category: null,
      location: undefined,
      type: 'reusable',
      quantity: null,
      unit: '',
      description: '',
    },
  });

  const watchType = form.watch('type');

  // Reset form when dialog opens/closes or item changes
  useEffect(() => {
    if (open) {
      // Reset invoice state
      setInvoiceFile(null);
      setInvoiceAmount('');
      setInvoiceCategory('采购');
      
      if (item) {
        form.reset({
          name: item.name,
          sku: item.sku,
          barcode: item.barcode || '',
          category: item.category || null,
          location: item.location,
          type: (item.item_type || item.type || 'reusable') as ItemType,
          quantity: item.quantity ?? null,
          unit: item.unit || '',
          description: item.description || '',
        });
      } else {
        form.reset({
          name: '',
          sku: '',
          barcode: '',
          category: null,
          location: undefined,
          type: 'reusable',
          quantity: null,
          unit: '',
          description: '',
        });
      }
    }
  }, [open, item, form]);

  // Handle invoice file selection - Requirements 23.1, 23.2
  const handleInvoiceFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      if (!ACCEPTED_INVOICE_TYPES.includes(file.type)) {
        return; // Invalid file type
      }
      setInvoiceFile(file);
    }
  };

  const removeInvoiceFile = () => {
    setInvoiceFile(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  const onSubmit = (data: ItemFormData) => {
    if (isEditing && item) {
      // Update existing item - only send editable fields
      const updateData: Record<string, unknown> = {
        name: data.name,
        barcode: data.barcode || null,
        category: data.category || null,
        location: data.location,
        unit: data.unit || '',
        description: data.description || '',
      };
      
      // Include quantity for reusable items
      if ((item.item_type || item.type) === 'reusable' && data.quantity !== undefined) {
        updateData.quantity = data.quantity ?? 1;
      }

      updateItem(
        { id: item.id, data: updateData },
        {
          onSuccess: () => {
            form.reset();
            onOpenChange(false);
            onSuccess?.();
          },
        }
      );
    } else {
      // Create new item
      const submitData = {
        name: data.name,
        sku: data.sku,
        barcode: data.barcode || null,
        category: data.category || null,
        location: data.location,
        type: data.type,
        quantity: data.type === 'consumable' 
          ? (data.quantity ?? 0) 
          : (data.quantity ?? 1),
        unit: data.unit || '',
        description: data.description || '',
      };

      createItem(submitData, {
        onSuccess: (createdItem) => {
          // If invoice file is provided, create invoice - Requirements 23.1
          if (invoiceFile) {
            // Validate invoice amount is provided
            if (!invoiceAmount || parseFloat(invoiceAmount) <= 0) {
              // Invoice file uploaded but no amount - skip invoice creation
              // This is intentional - user may not want to create invoice
              form.reset();
              onOpenChange(false);
              onSuccess?.();
              return;
            }
            
            createInvoice({
              name: data.name, // Use item name as invoice name - Requirements 23.3
              amount: parseFloat(invoiceAmount),
              category: invoiceCategory,
              item_id: createdItem.id,
              file: invoiceFile,
            }, {
              onSuccess: () => {
                form.reset();
                setInvoiceFile(null);
                setInvoiceAmount('');
                onOpenChange(false);
                onSuccess?.();
              },
              onError: () => {
                // Item was created but invoice failed
                // Still close the dialog and refresh
                form.reset();
                setInvoiceFile(null);
                setInvoiceAmount('');
                onOpenChange(false);
                onSuccess?.();
              },
            });
          } else {
            form.reset();
            onOpenChange(false);
            onSuccess?.();
          }
        },
      });
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[500px] max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>{isEditing ? '编辑物品' : '新增物品'}</DialogTitle>
        </DialogHeader>

        <Form {...form}>
          <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
            {/* 名称 */}
            <FormField
              control={form.control}
              name="name"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>名称 *</FormLabel>
                  <FormControl>
                    <Input placeholder="例如：MacBook Pro 14寸 / A4打印纸" {...field} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            {/* SKU */}
            <FormField
              control={form.control}
              name="sku"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>SKU *</FormLabel>
                  <FormControl>
                    <Input 
                      placeholder="例如：LAPTOP-001 / PAPER-A4-500" 
                      {...field} 
                      disabled={isEditing}
                    />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            {/* 类型 */}
            <FormField
              control={form.control}
              name="type"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>类型 *</FormLabel>
                  <Select
                    value={field.value}
                    onValueChange={field.onChange}
                    disabled={isEditing}
                  >
                    <FormControl>
                      <SelectTrigger className="w-full">
                        <SelectValue placeholder="选择物品类型" />
                      </SelectTrigger>
                    </FormControl>
                    <SelectContent>
                      <SelectItem value="reusable">可重复使用</SelectItem>
                      <SelectItem value="consumable">消耗品</SelectItem>
                    </SelectContent>
                  </Select>
                  <FormMessage />
                </FormItem>
              )}
            />

            {/* 数量 - 消耗品和可重复使用都显示 */}
            {watchType === 'consumable' && (
              <FormField
                control={form.control}
                name="quantity"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>数量 *</FormLabel>
                    <FormControl>
                      <Input
                        type="number"
                        min={0}
                        placeholder="例如：100"
                        {...field}
                        value={field.value ?? ''}
                        onChange={(e) => {
                          const val = e.target.value;
                          field.onChange(val === '' ? null : Number(val));
                        }}
                      />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
            )}
            
            {/* 数量 - 可重复使用物品 */}
            {watchType === 'reusable' && (
              <FormField
                control={form.control}
                name="quantity"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>数量</FormLabel>
                    <FormControl>
                      <Input
                        type="number"
                        min={1}
                        placeholder="默认为1"
                        {...field}
                        value={field.value ?? 1}
                        onChange={(e) => {
                          const val = e.target.value;
                          field.onChange(val === '' ? 1 : Number(val));
                        }}
                      />
                    </FormControl>
                    <FormDescription className="text-xs">
                      相同物品的数量，可同时借出多件
                    </FormDescription>
                    <FormMessage />
                  </FormItem>
                )}
              />
            )}

            {/* 分类 */}
            <FormField
              control={form.control}
              name="category"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>分类</FormLabel>
                  <FormControl>
                    <TreeSelect
                      nodes={categories || []}
                      value={field.value ?? undefined}
                      onChange={(val: number | undefined) => field.onChange(val ?? null)}
                      placeholder="选择分类"
                      loading={categoriesLoading}
                    />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            {/* 库位 */}
            <FormField
              control={form.control}
              name="location"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>库位 *</FormLabel>
                  <FormControl>
                    <TreeSelect
                      nodes={locations || []}
                      value={field.value}
                      onChange={field.onChange}
                      placeholder="选择库位"
                      loading={locationsLoading}
                      showCode
                    />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            {/* 条码 */}
            <FormField
              control={form.control}
              name="barcode"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>条码</FormLabel>
                  <FormControl>
                    <Input placeholder="可选，留空可自动生成" {...field} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            {/* 单位 */}
            <FormField
              control={form.control}
              name="unit"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>单位</FormLabel>
                  <FormControl>
                    <Input placeholder="如：个、件、箱" {...field} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            {/* 描述 */}
            <FormField
              control={form.control}
              name="description"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>描述</FormLabel>
                  <FormControl>
                    <Textarea
                      placeholder="例如：2023年采购，保修期至2026年 / 规格：500张/包"
                      className="resize-none"
                      rows={3}
                      {...field}
                    />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            {/* 发票上传 - 仅新增时显示 - Requirements 23.1, 23.2 */}
            {!isEditing && (
              <div className="space-y-3 pt-2 border-t">
                <FormLabel className="text-sm font-medium">发票信息（可选）</FormLabel>
                <FormDescription className="text-xs">
                  上传采购发票，支持 PDF、JPG、PNG 格式
                </FormDescription>
                
                {/* 发票文件上传 */}
                <div className="space-y-2">
                  <input
                    ref={fileInputRef}
                    type="file"
                    accept={ACCEPTED_INVOICE_EXTENSIONS}
                    onChange={handleInvoiceFileChange}
                    className="hidden"
                    id="invoice-file"
                  />
                  
                  {invoiceFile ? (
                    <div className="flex items-center gap-2 p-2 bg-muted rounded-md">
                      <FileText className="h-4 w-4 text-muted-foreground" />
                      <span className="flex-1 text-sm truncate">{invoiceFile.name}</span>
                      <Button
                        type="button"
                        variant="ghost"
                        size="sm"
                        onClick={removeInvoiceFile}
                        className="h-6 w-6 p-0"
                      >
                        <X className="h-4 w-4" />
                      </Button>
                    </div>
                  ) : (
                    <Button
                      type="button"
                      variant="outline"
                      size="sm"
                      onClick={() => fileInputRef.current?.click()}
                      className="w-full"
                    >
                      <Upload className="h-4 w-4 mr-2" />
                      选择发票文件
                    </Button>
                  )}
                </div>

                {/* 发票金额和类别 - 仅当有文件时显示 */}
                {invoiceFile && (
                  <div className="grid grid-cols-2 gap-3">
                    <div className="space-y-1">
                      <FormLabel className="text-xs">发票金额 *</FormLabel>
                      <Input
                        type="number"
                        step="0.01"
                        min="0"
                        placeholder="0.00"
                        value={invoiceAmount}
                        onChange={(e) => setInvoiceAmount(e.target.value)}
                      />
                    </div>
                    <div className="space-y-1">
                      <FormLabel className="text-xs">发票类别</FormLabel>
                      <Select value={invoiceCategory} onValueChange={setInvoiceCategory}>
                        <SelectTrigger>
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="采购">采购</SelectItem>
                          <SelectItem value="办公用品">办公用品</SelectItem>
                          <SelectItem value="设备">设备</SelectItem>
                          <SelectItem value="耗材">耗材</SelectItem>
                          <SelectItem value="其他">其他</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>
                  </div>
                )}
              </div>
            )}

            <DialogFooter className="flex-col sm:flex-row gap-2">
              {isEditing && (
                <AlertDialog>
                  <AlertDialogTrigger asChild>
                    <Button
                      type="button"
                      variant="destructive"
                      disabled={isPending}
                      className="sm:mr-auto"
                    >
                      <Trash2 className="h-4 w-4 mr-2" />
                      删除
                    </Button>
                  </AlertDialogTrigger>
                  <AlertDialogContent>
                    <AlertDialogHeader>
                      <AlertDialogTitle>确认删除物品？</AlertDialogTitle>
                      <AlertDialogDescription>
                        删除后物品数据将被永久移除，此操作不可恢复。
                      </AlertDialogDescription>
                    </AlertDialogHeader>
                    <AlertDialogFooter>
                      <AlertDialogCancel>取消</AlertDialogCancel>
                      <AlertDialogAction onClick={handleDelete}>
                        确认删除
                      </AlertDialogAction>
                    </AlertDialogFooter>
                  </AlertDialogContent>
                </AlertDialog>
              )}
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
