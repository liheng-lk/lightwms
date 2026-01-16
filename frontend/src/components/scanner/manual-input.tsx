'use client';

import { useState, useRef, useEffect, useCallback, type FormEvent } from 'react';
import { Keyboard, Search } from 'lucide-react';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';

export interface ManualInputProps {
  /** Callback when a barcode is submitted */
  onSubmit: (barcode: string) => void;
  /** Whether the input is disabled */
  disabled?: boolean;
  /** Whether to auto-focus the input */
  autoFocus?: boolean;
  /** Optional className for the container */
  className?: string;
  /** Placeholder text */
  placeholder?: string;
}

/**
 * ManualInput Component
 * 
 * Provides manual barcode input functionality for cases when
 * camera scanning is not available or barcode is damaged.
 * 
 * Features:
 * - Auto-focus on mount (configurable)
 * - Keyboard optimized (numeric input mode on mobile)
 * - Submit on Enter key
 * 
 * Requirements: 6.1, 6.3
 */
export function ManualInput({
  onSubmit,
  disabled = false,
  autoFocus = true,
  className,
  placeholder = '输入条码号...',
}: ManualInputProps) {
  const [value, setValue] = useState('');
  const inputRef = useRef<HTMLInputElement>(null);

  // Auto-focus on mount (Requirement 6.3)
  useEffect(() => {
    if (autoFocus && inputRef.current) {
      // Small delay to ensure the component is fully mounted
      const timer = setTimeout(() => {
        inputRef.current?.focus();
      }, 100);
      return () => clearTimeout(timer);
    }
  }, [autoFocus]);

  // Handle form submission
  const handleSubmit = useCallback((e: FormEvent) => {
    e.preventDefault();
    const trimmedValue = value.trim();
    if (trimmedValue && !disabled) {
      onSubmit(trimmedValue);
      setValue('');
      // Re-focus input for next entry
      inputRef.current?.focus();
    }
  }, [value, disabled, onSubmit]);

  // Handle input change
  const handleChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    setValue(e.target.value);
  }, []);

  return (
    <div className={cn('w-full', className)}>
      <form onSubmit={handleSubmit} className="flex gap-2">
        <div className="relative flex-1">
          <Keyboard className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            ref={inputRef}
            type="text"
            inputMode="text"
            autoComplete="off"
            autoCorrect="off"
            autoCapitalize="off"
            spellCheck={false}
            value={value}
            onChange={handleChange}
            disabled={disabled}
            placeholder={placeholder}
            className="pl-10"
          />
        </div>
        <Button 
          type="submit" 
          disabled={disabled || !value.trim()}
          size="default"
        >
          <Search className="h-4 w-4 mr-2" />
          查询
        </Button>
      </form>
      <p className="text-xs text-muted-foreground mt-2">
        手动输入条码号，按回车或点击查询按钮
      </p>
    </div>
  );
}
