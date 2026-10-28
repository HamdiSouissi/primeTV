/**
 * Client HTTP unique (axios) :
 * - injecte le JWT et le profil actif ;
 * - rafraîchit automatiquement le jeton expiré (une seule fois par requête) ;
 * - normalise les erreurs de l'API ({error: {code, message}}).
 */
import axios, { AxiosError, type AxiosInstance, type InternalAxiosRequestConfig } from 'axios';
import { reportApiStatus } from '@/store/apiStatus';

export const TOKEN_KEY = 'primetv.session';
const API_BASE = import.meta.env.VITE_API_BASE_URL ?? '/api/v1';

interface SessionShape {
  accessToken?: string;
  refreshToken?: string;
  profileId?: string;
}

function readSession(): SessionShape {
  try {
    const raw = localStorage.getItem(TOKEN_KEY);
    if (!raw) return {};
    const parsed = JSON.parse(raw) as { state?: SessionShape } | SessionShape;
    return (parsed as { state?: SessionShape }).state ?? (parsed as SessionShape);
  } catch {
    return {};
  }
}

export function writeSessionTokens(accessToken: string, refreshToken: string): void {
  const raw = localStorage.getItem(TOKEN_KEY);
  if (!raw) return;
  try {
    const parsed = JSON.parse(raw) as { state?: Record<string, unknown> };
    if (parsed.state) {
      parsed.state.accessToken = accessToken;
      parsed.state.refreshToken = refreshToken;
      localStorage.setItem(TOKEN_KEY, JSON.stringify(parsed));
    }
  } catch {
    /* stockage indisponible : ignoré */
  }
}

export const api: AxiosInstance = axios.create({
  baseURL: API_BASE,
  timeout: 45_000,
  headers: { 'Content-Type': 'application/json' },
});

api.interceptors.request.use((config: InternalAxiosRequestConfig) => {
  const session = readSession();
  if (session.accessToken) config.headers.Authorization = `Bearer ${session.accessToken}`;
  if (session.profileId) config.headers['X-Profile-Id'] = session.profileId;
  return config;
});

let refreshing: Promise<string | null> | null = null;

async function refreshAccessToken(): Promise<string | null> {
  const session = readSession();
  if (!session.refreshToken) return null;
  try {
    const { data } = await axios.post(`${API_BASE}/auth/refresh`, {
      refresh_token: session.refreshToken,
    });
    writeSessionTokens(data.access_token, data.refresh_token);
    return data.access_token as string;
  } catch {
    return null;
  }
}

api.interceptors.response.use(
  (response) => {
    // Une réponse (même 4xx) prouve que l'API est joignable.
    reportApiStatus('ok');
    return response;
  },
  async (error: AxiosError) => {
    const original = error.config as (InternalAxiosRequestConfig & { _retried?: boolean }) | undefined;
    const status = error.response?.status;

    // --- Diagnostic de connectivité (502/503/504 = proxy sans backend) --------
    if (status === 502 || status === 503 || status === 504) {
      reportApiStatus('unreachable', `HTTP ${status} sur ${error.config?.url ?? API_BASE}`);
    } else if (!error.response && error.code !== 'ERR_CANCELED' && !original?._retried) {
      reportApiStatus('offline', error.message);
    }

    if (error.response?.status === 401 && original && !original._retried) {
      original._retried = true;
      refreshing = refreshing ?? refreshAccessToken();
      const token = await refreshing;
      refreshing = null;
      if (token) {
        original.headers.Authorization = `Bearer ${token}`;
        return api(original);
      }
      localStorage.removeItem(TOKEN_KEY);
      if (!window.location.pathname.startsWith('/login')) window.location.assign('/login');
    }
    return Promise.reject(error);
  },
);

/** Message lisible d'une erreur API. */
export function apiErrorMessage(error: unknown, fallback = 'Une erreur est survenue'): string {
  if (axios.isAxiosError(error)) {
    const detail = (error.response?.data as { error?: { message?: string }; detail?: string } | undefined)?.error
      ?.message;
    if (detail) return detail;
    const rawDetail = (error.response?.data as { detail?: string } | undefined)?.detail;
    if (typeof rawDetail === 'string') return rawDetail;
    if (error.code === 'ECONNABORTED') return 'Le serveur met trop de temps à répondre';
    if (!error.response) return 'Serveur injoignable : vérifiez que l’API PrimeTV est démarrée';
  }
  if (error instanceof Error && error.message) return error.message;
  return fallback;
}
