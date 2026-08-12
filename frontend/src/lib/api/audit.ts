export interface AuditLogFilters {
  action?: string;
  target_type?: string;
  user?: number;
  search?: string;
  date_from?: string;
  date_to?: string;
  page?: number;
  page_size?: number;
  [key: string]: unknown;
}

export interface AuditLog {
  id: number;
  user: number | null;
  username?: string | null;
  action: string;
  target_type: string;
  target_id: number | null;
  target_repr?: string;
  changes?: Record<string, unknown> | null;
  metadata?: Record<string, unknown> | null;
  ip_address?: string | null;
  created_at: string;
  [key: string]: unknown;
}

export interface LoginLog {
  id: number;
  user: number | null;
  username?: string | null;
  ip_address?: string | null;
  user_agent?: string;
  success: boolean;
  failure_reason?: string;
  created_at: string;
  [key: string]: unknown;
}

export const ACTION_LABELS: Record<string, string> = {
  create: '创建', update: '更新', delete: '删除', deactivate: '停用',
  login: '登录', logout: '退出', borrow: '借用', return: '归还',
  take: '领用', replenish: '补货', import: '导入', export: '导出',
};

export const TARGET_TYPE_LABELS: Record<string, string> = {
  item: '物品', warehouse: '仓库', location: '库位', category: '分类',
  user: '用户', invite_code: '邀请码', borrow_record: '借用记录',
  take_record: '领用记录', replenish_record: '补货记录', invoice: '发票', system: '系统',
};
