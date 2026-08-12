export const itemTypeConfig = {
  reusable: { label: '可重复使用', variant: 'default' as const },
  consumable: { label: '消耗品', variant: 'secondary' as const },
};

export const itemStatusConfig = {
  available: { label: '可用', variant: 'default' as const },
  borrowed: { label: '借出中', variant: 'secondary' as const },
  out_of_stock: { label: '缺货', variant: 'destructive' as const },
  inactive: { label: '已停用', variant: 'outline' as const },
};

export const borrowStatusConfig = {
  active: { label: '借用中', variant: 'secondary' as const },
  returned: { label: '已归还', variant: 'default' as const },
  overdue: { label: '已逾期', variant: 'destructive' as const },
};

export const invoiceStatusConfig = {
  pending: { label: '未报销', variant: 'secondary' as const },
  reimbursed: { label: '已报销', variant: 'default' as const },
  rejected: { label: '无法报销', variant: 'destructive' as const },
};
