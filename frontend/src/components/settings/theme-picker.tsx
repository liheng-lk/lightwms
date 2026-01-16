'use client';

import { Check } from 'lucide-react';
import { Label } from '@/components/ui/label';
import { cn } from '@/lib/utils';
import { useTheme } from '@/providers/theme-provider';

export function ThemePicker() {
  const { theme, themes, setTheme } = useTheme();
  
  return (
    <div className="space-y-4">
      <div>
        <Label className="text-base font-medium">选择主题</Label>
        <p className="text-sm text-muted-foreground mb-3">选择一个界面主题风格</p>
      </div>
      
      <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
        {themes.map((t) => (
          <button
            key={t.id}
            onClick={() => setTheme(t.id)}
            className={cn(
              'relative rounded-lg border-2 p-3 transition-all text-left',
              theme.id === t.id
                ? 'border-primary ring-2 ring-primary/20'
                : 'border-border hover:border-primary/50'
            )}
          >
            {theme.id === t.id && (
              <div className="absolute top-2 right-2 bg-primary text-primary-foreground rounded-full p-0.5">
                <Check className="h-3 w-3" />
              </div>
            )}
            
            {/* Theme preview */}
            <div 
              className="h-16 rounded-md mb-2 overflow-hidden border"
              style={{ background: t.colors.background }}
            >
              <div 
                className="h-full w-1/3 flex flex-col"
                style={{ background: t.colors.sidebar }}
              >
                <div 
                  className="h-3 m-1 rounded-sm"
                  style={{ background: t.colors.sidebarPrimary }}
                />
                <div 
                  className="h-2 m-1 rounded-sm opacity-50"
                  style={{ background: t.colors.sidebarForeground }}
                />
                <div 
                  className="h-2 m-1 rounded-sm opacity-50"
                  style={{ background: t.colors.sidebarForeground }}
                />
              </div>
            </div>
            
            <div className="font-medium text-sm">{t.name}</div>
            <div className="text-xs text-muted-foreground">
              {t.isDark ? '深色模式' : '浅色模式'}
            </div>
          </button>
        ))}
      </div>
    </div>
  );
}
