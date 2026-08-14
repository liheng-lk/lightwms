'use client';

import { canAdministerSystem, canManageInventory } from '@/lib/permissions';
import { useAuth } from '@/providers/auth-provider';

/** Frontend mirror of the backend role contract. */
export function usePermissions() {
  const { user } = useAuth();
  const role = user?.role;

  const isSuperAdmin = role === 'super_admin';
  const isItemManager = role === 'item_manager';
  const isReadOnlyUser = role === 'read_only_user';
  const canManage = canManageInventory(role);

  // Existing component call sites may pass a resource, but owner metadata is
  // intentionally ignored: Item Manager is inventory-wide.
  const canCreate = () => canManage;
  const canEdit = (_resource?: unknown) => canManage;
  const canOperate = (_resource?: unknown) => canManage;
  const canDelete = (_resource?: unknown) => canManage;
  const canViewAuditLogs = () => canAdministerSystem(role);

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
