/** État d'authentification persistant (JWT + profil actif). */
import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import { TOKEN_KEY } from '@/api/client';
import type { Profile, Tokens, User } from '@/api/types';

interface AuthState {
  user: User | null;
  accessToken: string | null;
  refreshToken: string | null;
  profiles: Profile[];
  profileId: string | null;
  setSession: (tokens: Tokens) => void;
  setUser: (user: User) => void;
  setProfiles: (profiles: Profile[]) => void;
  setProfileId: (profileId: string) => void;
  logout: () => void;
  isAuthenticated: () => boolean;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      user: null,
      accessToken: null,
      refreshToken: null,
      profiles: [],
      profileId: null,
      setSession: (tokens) =>
        set({
          user: tokens.user,
          accessToken: tokens.access_token,
          refreshToken: tokens.refresh_token,
        }),
      setUser: (user) => set({ user }),
      setProfiles: (profiles) => {
        const current = get().profileId;
        const stillExists = profiles.some((profile) => profile.id === current);
        const fallback = profiles.find((profile) => profile.is_default) ?? profiles[0];
        set({ profiles, profileId: stillExists ? current : (fallback?.id ?? null) });
      },
      setProfileId: (profileId) => set({ profileId }),
      logout: () => set({ user: null, accessToken: null, refreshToken: null, profiles: [], profileId: null }),
      isAuthenticated: () => Boolean(get().accessToken),
    }),
    {
      name: TOKEN_KEY,
      partialize: (state) => ({
        user: state.user,
        accessToken: state.accessToken,
        refreshToken: state.refreshToken,
        profileId: state.profileId,
      }),
    },
  ),
);
