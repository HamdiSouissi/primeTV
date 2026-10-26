/** Préférences d'interface : thème, sidebar, lecteur. */
import { create } from 'zustand';
import { persist } from 'zustand/middleware';

type Theme = 'dark' | 'light';

interface UiState {
  theme: Theme;
  sidebarOpen: boolean;
  playerChannelId: string | null;
  toggleTheme: () => void;
  setTheme: (theme: Theme) => void;
  setSidebarOpen: (open: boolean) => void;
  openPlayer: (channelId: string) => void;
  closePlayer: () => void;
}

function applyTheme(theme: Theme) {
  const root = document.documentElement;
  root.classList.toggle('dark', theme === 'dark');
  root.style.colorScheme = theme;
}

export const useUiStore = create<UiState>()(
  persist(
    (set, get) => ({
      theme: 'dark',
      sidebarOpen: false,
      playerChannelId: null,
      toggleTheme: () => {
        const theme = get().theme === 'dark' ? 'light' : 'dark';
        applyTheme(theme);
        set({ theme });
      },
      setTheme: (theme) => {
        applyTheme(theme);
        set({ theme });
      },
      setSidebarOpen: (sidebarOpen) => set({ sidebarOpen }),
      openPlayer: (playerChannelId) => set({ playerChannelId }),
      closePlayer: () => set({ playerChannelId: null }),
    }),
    {
      name: 'primetv.ui',
      partialize: (state) => ({ theme: state.theme }),
      onRehydrateStorage: () => (state) => {
        if (state?.theme) applyTheme(state.theme);
      },
    },
  ),
);

/** Applique le thème stocké au premier rendu. */
export function bootstrapTheme(): void {
  const stored = localStorage.getItem('primetv.ui');
  let theme: Theme = 'dark';
  try {
    theme = (JSON.parse(stored ?? '{}')?.state?.theme as Theme) ?? 'dark';
  } catch {
    theme = 'dark';
  }
  applyTheme(theme);
}
