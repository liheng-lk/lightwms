import { Badge } from '@/components/ui/badge';
import { itemStatusConfig, borrowStatusConfig, itemTypeConfig } from '@/lib/types/ui';
import { cn } from '@/lib/utils';

type ItemStatus = keyof typeof itemStatusConfig;
type BorrowStatus = keyof typeof borrowStatusConfig;
type ItemType = keyof typeof itemTypeConfig;

interface StatusBadgeProps {
  status: ItemStatus | BorrowStatus;
  type?: 'item' | 'borrow';
  className?: string;
}

export function StatusBadge({ status, type = 'item', className }: StatusBadgeProps) {
  const config = type === 'item' 
    ? itemStatusConfig[status as ItemStatus] 
    : borrowStatusConfig[status as BorrowStatus];
  
  if (!config) return null;
  
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

interface ItemTypeBadgeProps {
  itemType?: ItemType;
  className?: string;
}

export function ItemTypeBadge({ itemType, className }: ItemTypeBadgeProps) {
  if (!itemType) return null;
  
  const config = itemTypeConfig[itemType];
  
  if (!config) return null;
  
  return (
    <Badge variant={config.variant} className={className}>
      {config.label}
    </Badge>
  );
}
