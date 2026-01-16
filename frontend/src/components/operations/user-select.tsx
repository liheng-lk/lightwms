'use client';

import { useState, useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Input } from '@/components/ui/input';
import { getUsers } from '@/lib/api/users';

interface UserSelectProps {
  value?: number;
  onChange: (value: number | undefined) => void;
  placeholder?: string;
}

export function UserSelect({ value, onChange, placeholder = '选择用户' }: UserSelectProps) {
  const [search, setSearch] = useState('');
  
  const { data } = useQuery({
    queryKey: ['users', { search }],
    queryFn: () => getUsers({ search, page_size: 50 }),
  });
  
  const users = data?.results || [];
  
  return (
    <Select
      value={value ? String(value) : ''}
      onValueChange={(v) => onChange(v ? Number(v) : undefined)}
    >
      <SelectTrigger>
        <SelectValue placeholder={placeholder} />
      </SelectTrigger>
      <SelectContent>
        <div className="p-2">
          <Input
            placeholder="输入用户名搜索..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="h-8"
          />
        </div>
        {users.length === 0 ? (
          <div className="p-2 text-sm text-muted-foreground text-center">
            {search ? '未找到用户' : '暂无用户'}
          </div>
        ) : (
          users.map((user) => (
            <SelectItem key={user.id} value={String(user.id)}>
              {user.username}
              {user.department && (
                <span className="text-muted-foreground ml-2">({user.department})</span>
              )}
            </SelectItem>
          ))
        )}
      </SelectContent>
    </Select>
  );
}
