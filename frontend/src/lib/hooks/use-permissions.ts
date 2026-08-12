'use client';
import { useAuth } from '@/providers/auth-provider';

type OwnedResource = { owner_id?: number | null; owner?: number | { id?: number | null } | null } | null | undefined;
function ownerId(resource: OwnedResource): number | null {
  if (!resource) return null;
  if (typeof resource.owner_id === 'number') return resource.owner_id;
  if (typeof resource.owner === 'number') return resource.owner;
  if (resource.owner && typeof resource.owner === 'object' && typeof resource.owner.id === 'number') return resource.owner.id;
  return null;
}
export function usePermissions() {
  const { user } = useAuth();
  const isSuperAdmin = user?.role === 'super_admin';
  const isItemManager = user?.role === 'item_manager';
  const isReadOnlyUser = user?.role === 'read_only_user';
  const canManage = isSuperAdmin || isItemManager;
  const canCreate = () => canManage;
  const canEdit = (resource?: OwnedResource) => isSuperAdmin || (isItemManager && (ownerId(resource) === null || ownerId(resource) === user?.id));
  const canDelete = (resource?: OwnedResource) => isSuperAdmin || (isItemManager && !!resource && ownerId(resource) === user?.id);
  return { isSuperAdmin, isItemManager, isReadOnlyUser, canManage, canCreate, canEdit, canDelete, canBorrow: () => !!user, canTake: () => !!user };
}
