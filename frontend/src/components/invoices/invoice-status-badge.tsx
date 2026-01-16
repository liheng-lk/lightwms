'use client';

import { Badge } from '@/components/ui/badge';
import { invoiceStatusConfig } from '@/lib/types/ui';
import { cn } from '@/lib/utils';
import type { InvoiceStatus } from '@/lib/types';

interface InvoiceStatusBadgeProps {
  status: InvoiceStatus;
  className?: string;
}

export function InvoiceStatusBadge({ status, className }: InvoiceStatusBadgeProps) {
  const config = invoiceStatusConfig[status];
  
  if (!config) {
    return <Badge variant="outline">{status}</Badge>;
  }

  const variantClasses = {
    success: 'bg-green-100 text-green-800 hover:bg-green-100',
    warning: 'bg-yellow-100 text-yellow-800 hover:bg-yellow-100',
    destructive: 'bg-red-100 text-red-800 hover:bg-red-100',
    default: 'bg-blue-100 text-blue-800 hover:bg-blue-100',
    secondary: 'bg-gray-100 text-gray-800 hover:bg-gray-100',
    outline: 'border-gray-300 text-gray-700',
  };

  return (
    <Badge 
      variant="outline" 
      className={cn(variantClasses[config.variant], className)}
    >
      {config.label}
    </Badge>
  );
}
