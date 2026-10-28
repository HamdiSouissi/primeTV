/**
 * État de la liaison avec l'API, alimenté par le client axios.
 *
 * Objectif : ne plus laisser l'utilisateur devant une connexion qui « ne marche
 * pas » sans explication. Toute réponse 502/503/504 (proxy Nginx sans backend)
 * ou toute absence de réponse (réseau, service arrêté) bascule l'application en
 * mode « API injoignable » et affiche une bannière avec la cause probable.
 */
import { create } from 'zustand';

export type ApiStatus = 'ok' | 'unreachable' | 'offline';

interface ApiStatusState {
  status: ApiStatus;
  /** Message technique (code HTTP, endpoint) pour l'affichage et le support. */
  detail: string | null;
  /** Horodatage de la dernière erreur détectée. */
  since: number | null;
  setStatus: (status: ApiStatus, detail?: string | null) => void;
  reset: () => void;
}

export const useApiStatusStore = create<ApiStatusState>((set) => ({
  status: 'ok',
  detail: null,
  since: null,
  setStatus: (status, detail = null) =>
    set((state) => {
      // On conserve la date de la première occurrence pour afficher « depuis … ».
      if (state.status === status) return { detail };
      return { status, detail, since: status === 'ok' ? null : Date.now() };
    }),
  reset: () => set({ status: 'ok', detail: null, since: null }),
}));

/** Met à jour l'état global depuis un intercepteur (hors composant React). */
export function reportApiStatus(status: ApiStatus, detail?: string | null): void {
  useApiStatusStore.getState().setStatus(status, detail);
}
