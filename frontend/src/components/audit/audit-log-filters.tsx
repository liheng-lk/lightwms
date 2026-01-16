'use client';

import { useState, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Search, X } from 'lucide-react';
import { AuditLogFilters } from '@/lib/api/audit';
import { ACTION_LABELS, TARGET_TYPE_LABELS } from '@/lib/api/audit';
import { getUsers } from '@/lib/api/users';
import type { User } from '@/lib/types';

interface AuditLogFiltersProps {
  filters: AuditLogFilters;
  onFiltersChange: (filters: Partial<AuditLogFilters>) => void;
  onReset: () => void;
}

export function AuditLogFiltersComponent({
  filters,
  onFiltersChange,
  onReset,
}: AuditLogFiltersProps) {
  const [users, setUsers] = useState<User[]>([]);
  const [loadingUsers, setLoadingUsers] = useState(false);

  // Load users for filter dropdown
  useEffect(() => {
    async function loadUsers() {
      setLoadingUsers(true);
      try {
        const response = await getUsers({ page_size: 100 });
        setUsers(response.results);
      } catch (error) {
        console.error('Failed to load users:', error);
      } finally {
        setLoadingUsers(false);
      }
    }
    loadUsers();
  }, []);

  const hasFilters = filters.action || filters.target_type || filters.operator_id || filters.date_from || filters.date_to;

  return (
    <div className="space-y-4 p-4 bg-muted/50 rounded-lg">
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4">
        {/* User filter */}
        <div className="space-y-2">
          <Label>操作用户</Label>
          <Select
            value={filters.operator_id?.toString() || 'all'}
            onValueChange={(value) =>
              onFiltersChange({ operator_id: value === 'all' ? undefined : Number(value) })
            }
          >
            <SelectTrigger>
              <SelectValue placeholder="全部用户" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">全部用户</SelectItem>
              {users.map((user) => (
                <SelectItem key={user.id} value={user.id.toString()}>
                  {user.username}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        {/* Action filter */}
        <div className="space-y-2">
          <Label>操作类型</Label>
          <Select
            value={filters.action || 'all'}
            onValueChange={(value) =>
              onFiltersChange({ action: value === 'all' ? undefined : value })
            }
          >
            <SelectTrigger>
              <SelectValue placeholder="全部操作" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">全部操作</SelectItem>
              {Object.entries(ACTION_LABELS).map(([value, label]) => (
                <SelectItem key={value} value={value}>
                  {label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        {/* Target type filter */}
        <div className="space-y-2">
          <Label>目标类型</Label>
          <Select
            value={filters.target_type || 'all'}
            onValueChange={(value) =>
              onFiltersChange({ target_type: value === 'all' ? undefined : value })
            }
          >
            <SelectTrigger>
              <SelectValue placeholder="全部类型" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">全部类型</SelectItem>
              {Object.entries(TARGET_TYPE_LABELS).map(([value, label]) => (
                <SelectItem key={value} value={value}>
                  {label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        {/* Date from */}
        <div className="space-y-2">
          <Label>开始日期</Label>
          <Input
            type="date"
            value={filters.date_from?.split('T')[0] || ''}
            onChange={(e) =>
              onFiltersChange({
                date_from: e.target.value ? `${e.target.value}T00:00:00` : undefined,
              })
            }
          />
        </div>

        {/* Date to */}
        <div className="space-y-2">
          <Label>结束日期</Label>
          <Input
            type="date"
            value={filters.date_to?.split('T')[0] || ''}
            onChange={(e) =>
              onFiltersChange({
                date_to: e.target.value ? `${e.target.value}T23:59:59` : undefined,
              })
            }
          />
        </div>
      </div>

      {hasFilters && (
        <div className="flex justify-end">
          <Button variant="ghost" size="sm" onClick={onReset}>
            <X className="h-4 w-4 mr-1" />
            清除筛选
          </Button>
        </div>
      )}
    </div>
  );
}
