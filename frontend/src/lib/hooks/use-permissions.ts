'use client';

import { useAuth } from '@/providers/auth-provider';

/**
 * Frontend mirror of the backend role contract.
 *
 * Item Manager is an inventory-wide business role. `owner` is responsibility
 * metadata/filtering information and must never be used to hide normal
 * inventory actions from an Item Manager.
 */
export function usePermissions() {
  const { user } = useAuth();

  const isSuperAdmin = user?.role === 'super_admin';
  const isItemManager = user?.role === 'item_manager';
  const isReadOnlyUser = user?.role === 'read_only_user';
  const canManage = isSuperAdmin || isItemManager;

  // Keep the optional resource argument for existing component call sites,
  // but authorization intentionally does not depend on resource.owner.
  const canCreate = () => canManage;
  const canEdit = (_resource?: unknown) => canManage;
  const canOperate = (_resource?: unknown) => canManage;
  const canDelete = (_resource?: unknown) => canManage;

  // Audit logs are a system-administration capability in the current role
  // matrix and are exposed in navigation to Super Admin only.
  const canViewAuditLogs = () => isSuperAdmin;

  return {
    isSuperAdmin,
    isItemManager,
    isReadOnlyUser,
    canManage,
    canCreate,
    canEdit,
    canOperate,
    canDelete,
    canViewAuditLogs,
    canBorrow: () => canManage,
    canTake: () => canManage,
  };
}
