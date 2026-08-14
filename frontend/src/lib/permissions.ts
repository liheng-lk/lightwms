export type AppRole = 'super_admin' | 'item_manager' | 'read_only_user';

/** All authenticated warehouse roles may read active inventory. */
export function canReadInventory(role: AppRole | null | undefined): boolean {
  return role === 'super_admin' || role === 'item_manager' || role === 'read_only_user';
}

/**
 * Inventory business management is global for Super Admin and Item Manager.
 * Resource owner IDs intentionally do not participate in this decision.
 */
export function canManageInventory(role: AppRole | null | undefined): boolean {
  return role === 'super_admin' || role === 'item_manager';
}

/** System administration remains Super Admin only. */
export function canAdministerSystem(role: AppRole | null | undefined): boolean {
  return role === 'super_admin';
}
