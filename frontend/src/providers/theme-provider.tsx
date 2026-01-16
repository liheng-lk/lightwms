'use client';

import {
  createContext,
  useContext,
  useEffect,
  useState,
  useCallback,
  ReactNode,
} from 'react';

// 主题配置类型
export interface ThemeConfig {
  id: string;
  name: string;
  colors: {
    primary: string;
    primaryForeground: string;
    background: string;
    foreground: string;
    card: string;
    cardForeground: string;
    muted: string;
    mutedForeground: string;
    accent: string;
    accentForeground: string;
    sidebar: string;
    sidebarForeground: string;
    sidebarPrimary: string;
    sidebarPrimaryForeground: string;
    sidebarAccent: string;
    sidebarAccentForeground: string;
  };
  isDark: boolean;
}

// 系统设置类型（本地存储）
export interface LocalSettings {
  themeId: string;
  backgroundImage?: string;
  backgroundColor?: string;
}

// 系统设置类型（包含服务端 Logo）
export interface SystemSettings extends LocalSettings {
  customLogo?: string;
}

// 预设主题
export const themes: ThemeConfig[] = [
  {
    id: 'light',
    name: '浅色',
    isDark: false,
    colors: {
      primary: '#171717',
      primaryForeground: '#fafafa',
      background: '#ffffff',
      foreground: '#0a0a0a',
      card: '#ffffff',
      cardForeground: '#0a0a0a',
      muted: '#f5f5f5',
      mutedForeground: '#737373',
      accent: '#f5f5f5',
      accentForeground: '#171717',
      sidebar: '#fafafa',
      sidebarForeground: '#0a0a0a',
      sidebarPrimary: '#171717',
      sidebarPrimaryForeground: '#fafafa',
      sidebarAccent: '#f5f5f5',
      sidebarAccentForeground: '#171717',
    },
  },
  {
    id: 'dark',
    name: '深色',
    isDark: true,
    colors: {
      primary: '#fafafa',
      primaryForeground: '#171717',
      background: '#0a0a0a',
      foreground: '#fafafa',
      card: '#171717',
      cardForeground: '#fafafa',
      muted: '#262626',
      mutedForeground: '#a3a3a3',
      accent: '#262626',
      accentForeground: '#fafafa',
      sidebar: '#171717',
      sidebarForeground: '#fafafa',
      sidebarPrimary: '#3b82f6',
      sidebarPrimaryForeground: '#fafafa',
      sidebarAccent: '#262626',
      sidebarAccentForeground: '#fafafa',
    },
  },
  {
    id: 'blue',
    name: '蓝色',
    isDark: false,
    colors: {
      primary: '#2563eb',
      primaryForeground: '#ffffff',
      background: '#f0f9ff',
      foreground: '#1e3a5f',
      card: '#ffffff',
      cardForeground: '#1e3a5f',
      muted: '#e0f2fe',
      mutedForeground: '#64748b',
      accent: '#dbeafe',
      accentForeground: '#1e3a5f',
      sidebar: '#1e40af',
      sidebarForeground: '#f0f9ff',
      sidebarPrimary: '#60a5fa',
      sidebarPrimaryForeground: '#1e3a5f',
      sidebarAccent: '#2563eb',
      sidebarAccentForeground: '#f0f9ff',
    },
  },
  {
    id: 'green',
    name: '绿色',
    isDark: false,
    colors: {
      primary: '#16a34a',
      primaryForeground: '#ffffff',
      background: '#f0fdf4',
      foreground: '#14532d',
      card: '#ffffff',
      cardForeground: '#14532d',
      muted: '#dcfce7',
      mutedForeground: '#64748b',
      accent: '#bbf7d0',
      accentForeground: '#14532d',
      sidebar: '#166534',
      sidebarForeground: '#f0fdf4',
      sidebarPrimary: '#4ade80',
      sidebarPrimaryForeground: '#14532d',
      sidebarAccent: '#22c55e',
      sidebarAccentForeground: '#f0fdf4',
    },
  },
  {
    id: 'purple',
    name: '紫色',
    isDark: false,
    colors: {
      primary: '#9333ea',
      primaryForeground: '#ffffff',
      background: '#faf5ff',
      foreground: '#3b0764',
      card: '#ffffff',
      cardForeground: '#3b0764',
      muted: '#f3e8ff',
      mutedForeground: '#64748b',
      accent: '#e9d5ff',
      accentForeground: '#3b0764',
      sidebar: '#6b21a8',
      sidebarForeground: '#faf5ff',
      sidebarPrimary: '#c084fc',
      sidebarPrimaryForeground: '#3b0764',
      sidebarAccent: '#a855f7',
      sidebarAccentForeground: '#faf5ff',
    },
  },
];

// 预设背景选项
export const presetBackgrounds = [
  { id: 'none', name: '无背景', value: '' },
  { id: 'gradient-blue', name: '蓝色渐变', value: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)' },
  { id: 'gradient-green', name: '绿色渐变', value: 'linear-gradient(135deg, #11998e 0%, #38ef7d 100%)' },
  { id: 'gradient-orange', name: '橙色渐变', value: 'linear-gradient(135deg, #f093fb 0%, #f5576c 100%)' },
  { id: 'gradient-gray', name: '灰色渐变', value: 'linear-gradient(135deg, #bdc3c7 0%, #2c3e50 100%)' },
];

const STORAGE_KEY = 'lightwms-theme-settings';
const DEFAULT_LOCAL_SETTINGS: LocalSettings = {
  themeId: 'light',
  backgroundImage: '',
  backgroundColor: '',
};

const DEFAULT_SETTINGS: SystemSettings = {
  ...DEFAULT_LOCAL_SETTINGS,
  customLogo: '',
};

interface ThemeContextValue {
  theme: ThemeConfig;
  themes: ThemeConfig[];
  settings: SystemSettings;
  setTheme: (themeId: string) => void;
  updateSettings: (settings: Partial<LocalSettings>) => void;
  resetSettings: () => void;
  refreshLogo: () => Promise<void>;
}

const ThemeContext = createContext<ThemeContextValue | undefined>(undefined);

function getStoredSettings(): LocalSettings {
  if (typeof window === 'undefined') return DEFAULT_LOCAL_SETTINGS;
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored) {
      const parsed = JSON.parse(stored);
      // Only return local settings (exclude customLogo which is now server-side)
      return {
        themeId: parsed.themeId || DEFAULT_LOCAL_SETTINGS.themeId,
        backgroundImage: parsed.backgroundImage || '',
        backgroundColor: parsed.backgroundColor || '',
      };
    }
  } catch {
    // ignore parse errors
  }
  return DEFAULT_LOCAL_SETTINGS;
}

function saveSettings(settings: LocalSettings) {
  if (typeof window === 'undefined') return;
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(settings));
  } catch {
    // ignore storage errors
  }
}

function applyTheme(theme: ThemeConfig) {
  const root = document.documentElement;
  
  // Apply CSS variables
  root.style.setProperty('--primary', theme.colors.primary);
  root.style.setProperty('--primary-foreground', theme.colors.primaryForeground);
  root.style.setProperty('--background', theme.colors.background);
  root.style.setProperty('--foreground', theme.colors.foreground);
  root.style.setProperty('--card', theme.colors.card);
  root.style.setProperty('--card-foreground', theme.colors.cardForeground);
  root.style.setProperty('--muted', theme.colors.muted);
  root.style.setProperty('--muted-foreground', theme.colors.mutedForeground);
  root.style.setProperty('--accent', theme.colors.accent);
  root.style.setProperty('--accent-foreground', theme.colors.accentForeground);
  root.style.setProperty('--sidebar', theme.colors.sidebar);
  root.style.setProperty('--sidebar-foreground', theme.colors.sidebarForeground);
  root.style.setProperty('--sidebar-primary', theme.colors.sidebarPrimary);
  root.style.setProperty('--sidebar-primary-foreground', theme.colors.sidebarPrimaryForeground);
  root.style.setProperty('--sidebar-accent', theme.colors.sidebarAccent);
  root.style.setProperty('--sidebar-accent-foreground', theme.colors.sidebarAccentForeground);
  
  // Toggle dark class
  if (theme.isDark) {
    root.classList.add('dark');
  } else {
    root.classList.remove('dark');
  }
}

function applyBackground(settings: SystemSettings) {
  const body = document.body;
  
  if (settings.backgroundImage) {
    // Check if it's a gradient or image URL
    if (settings.backgroundImage.startsWith('linear-gradient') || 
        settings.backgroundImage.startsWith('radial-gradient')) {
      body.style.backgroundImage = settings.backgroundImage;
      body.style.backgroundSize = 'cover';
      body.style.backgroundAttachment = 'fixed';
    } else {
      body.style.backgroundImage = `url(${settings.backgroundImage})`;
      body.style.backgroundSize = 'cover';
      body.style.backgroundPosition = 'center';
      body.style.backgroundAttachment = 'fixed';
    }
  } else {
    body.style.backgroundImage = '';
  }
  
  if (settings.backgroundColor && !settings.backgroundImage) {
    body.style.backgroundColor = settings.backgroundColor;
  } else if (!settings.backgroundImage) {
    body.style.backgroundColor = '';
  }
}

export function ThemeProvider({ children }: { children: ReactNode }) {
  const [settings, setSettings] = useState<SystemSettings>(DEFAULT_SETTINGS);
  const [mounted, setMounted] = useState(false);
  
  // Fetch logo from server
  const fetchLogo = useCallback(async () => {
    try {
      const response = await fetch('/api/system-settings/');
      if (response.ok) {
        const data = await response.json();
        if (data.logo_url) {
          // Convert /media/xxx to /api/media/xxx for frontend proxy
          let logoUrl = data.logo_url;
          if (logoUrl.startsWith('/media/')) {
            logoUrl = '/api' + logoUrl;
          }
          setSettings(prev => ({ ...prev, customLogo: logoUrl }));
        }
      }
    } catch {
      // Ignore fetch errors - use default logo
    }
  }, []);
  
  // Load settings from localStorage on mount
  useEffect(() => {
    const stored = getStoredSettings();
    setSettings(prev => ({ ...prev, ...stored }));
    setMounted(true);
    
    // Fetch logo from server
    fetchLogo();
  }, [fetchLogo]);
  
  // Apply theme and background when settings change
  useEffect(() => {
    if (!mounted) return;
    
    const theme = themes.find(t => t.id === settings.themeId) || themes[0];
    applyTheme(theme);
    applyBackground(settings);
  }, [settings, mounted]);
  
  const theme = themes.find(t => t.id === settings.themeId) || themes[0];
  
  const setTheme = useCallback((themeId: string) => {
    setSettings(prev => {
      const newSettings = { ...prev, themeId };
      saveSettings({ themeId, backgroundImage: prev.backgroundImage, backgroundColor: prev.backgroundColor });
      return newSettings;
    });
  }, []);
  
  const updateSettings = useCallback((newSettings: Partial<LocalSettings>) => {
    setSettings(prev => {
      const updated = { ...prev, ...newSettings };
      saveSettings({ themeId: updated.themeId, backgroundImage: updated.backgroundImage, backgroundColor: updated.backgroundColor });
      return updated;
    });
  }, []);
  
  const resetSettings = useCallback(() => {
    setSettings(prev => ({ ...DEFAULT_SETTINGS, customLogo: prev.customLogo }));
    saveSettings(DEFAULT_LOCAL_SETTINGS);
  }, []);
  
  const refreshLogo = useCallback(async () => {
    await fetchLogo();
  }, [fetchLogo]);
  
  // Always render children - CSS has default styles in globals.css
  // This prevents flash of empty content
  return (
    <ThemeContext.Provider
      value={{
        theme,
        themes,
        settings,
        setTheme,
        updateSettings,
        resetSettings,
        refreshLogo,
      }}
    >
      {children}
    </ThemeContext.Provider>
  );
}

export function useTheme() {
  const context = useContext(ThemeContext);
  if (!context) {
    throw new Error('useTheme must be used within ThemeProvider');
  }
  return context;
}
