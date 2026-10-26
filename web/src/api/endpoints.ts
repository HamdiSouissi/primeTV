/** Toutes les routes de l'API PrimeTV, typées et regroupées par domaine. */
import { api } from './client';
import type {
  ActivityEntry,
  Channel,
  ChannelQuery,
  DashboardStats,
  EpgSource,
  Facets,
  Favorite,
  HistoryEntry,
  ImportResult,
  NowNext,
  Page,
  Playback,
  Playlist,
  Profile,
  Programme,
  Provider,
  PublicConfig,
  ScanJob,
  SettingsEntry,
  Tokens,
  User,
} from './types';

const unwrap = <T>(promise: Promise<{ data: T }>): Promise<T> => promise.then((response) => response.data);

export const authApi = {
  login: (email: string, password: string) =>
    unwrap<Tokens>(api.post('/auth/login', { email, password })),
  register: (payload: { email: string; username: string; password: string; full_name?: string }) =>
    unwrap<Tokens>(api.post('/auth/register', payload)),
  me: () => unwrap<User>(api.get('/auth/me')),
  updateMe: (payload: Partial<Pick<User, 'full_name' | 'email' | 'username'>>) =>
    unwrap<User>(api.patch('/auth/me', payload)),
  changePassword: (current_password: string, new_password: string) =>
    unwrap<{ message: string }>(api.post('/auth/change-password', { current_password, new_password })),
};

export const profilesApi = {
  list: () => unwrap<Profile[]>(api.get('/profiles')),
  create: (payload: Record<string, unknown>) => unwrap<Profile>(api.post('/profiles', payload)),
  update: (id: string, payload: Record<string, unknown>) =>
    unwrap<Profile>(api.patch(`/profiles/${id}`, payload)),
  remove: (id: string) => unwrap<{ message: string }>(api.delete(`/profiles/${id}`)),
};

export const catalogApi = {
  config: () => unwrap<PublicConfig>(api.get('/config')),
  facets: () => unwrap<Facets>(api.get('/catalog/facets')),
  categories: () => unwrap<Facets['categories']>(api.get('/catalog/categories')),
  languages: () => unwrap<Facets['languages']>(api.get('/catalog/languages')),
  bouquets: () => unwrap<Facets['bouquets']>(api.get('/catalog/bouquets')),
  quickFilters: () =>
    unwrap<{ id?: string; slug?: string; name: string; count: number; color?: string; icon?: string; flag?: string }[]>(
      api.get('/catalog/quick-filters'),
    ),
};

export const channelsApi = {
  list: (query: ChannelQuery = {}) => unwrap<Page<Channel>>(api.get('/channels', { params: query })),
  get: (id: string) => unwrap<Channel>(api.get(`/channels/${id}`)),
  update: (id: string, payload: Record<string, unknown>) => unwrap<Channel>(api.patch(`/channels/${id}`, payload)),
  remove: (id: string) => unwrap<{ message: string }>(api.delete(`/channels/${id}`)),
  refresh: (id: string) => unwrap<Record<string, unknown>>(api.post(`/channels/${id}/refresh`)),
  play: (id: string, useProxy = true) =>
    unwrap<Playback>(api.get(`/channels/${id}/play`, { params: { proxy: useProxy } })),
  epg: (id: string) => unwrap<NowNext>(api.get(`/channels/${id}/epg`)),
  setKey: (id: string, kid: string, key: string) =>
    unwrap<{ message: string }>(api.put(`/channels/${id}/keys`, { kid, key })),
  removeKey: (id: string, kid: string) =>
    unwrap<{ message: string }>(api.delete(`/channels/${id}/keys/${kid}`)),
};

export const providersApi = {
  list: () => unwrap<Provider[]>(api.get('/providers')),
  create: (payload: Record<string, unknown>) => unwrap<Provider>(api.post('/providers', payload)),
  update: (id: string, payload: Record<string, unknown>) => unwrap<Provider>(api.patch(`/providers/${id}`, payload)),
  remove: (id: string) => unwrap<{ message: string }>(api.delete(`/providers/${id}`)),
  test: (id: string) => unwrap<{ ok: boolean; message: string }>(api.post(`/providers/${id}/test`)),
  previewXtream: (params: { base_url: string; username: string; password: string }) =>
    unwrap<Record<string, unknown>>(api.post('/providers/xtream/preview', null, { params })),
};

export const playlistsApi = {
  list: () => unwrap<Playlist[]>(api.get('/playlists')),
  importUrl: (payload: {
    name?: string;
    url: string;
    provider_id?: string | null;
    replace?: boolean;
    epg_url?: string;
  }) => unwrap<ImportResult>(api.post('/playlists', { ...payload, source_type: 'url' })),
  importText: (payload: { name?: string; content: string; provider_id?: string | null }) =>
    unwrap<ImportResult>(api.post('/playlists', { ...payload, source_type: 'text', replace: true })),
  importFile: (file: File, name?: string, providerId?: string) => {
    const form = new FormData();
    form.append('file', file);
    if (name) form.append('name', name);
    if (providerId) form.append('provider_id', providerId);
    form.append('replace', 'true');
    return unwrap<ImportResult>(
      api.post('/playlists/upload', form, { headers: { 'Content-Type': 'multipart/form-data' } }),
    );
  },
  importXtream: (payload: { name?: string; base_url: string; username: string; password: string; epg?: boolean }) =>
    unwrap<ImportResult>(api.post('/playlists/xtream', payload)),
  sync: (id: string) => unwrap<ImportResult>(api.post(`/playlists/${id}/sync`)),
  update: (id: string, payload: Partial<Pick<Playlist, 'name' | 'is_active' | 'auto_sync'>>) =>
    unwrap<Playlist>(api.patch(`/playlists/${id}`, payload)),
  remove: (id: string) => unwrap<{ message: string }>(api.delete(`/playlists/${id}`)),
};

export const epgApi = {
  list: () => unwrap<EpgSource[]>(api.get('/epg/sources')),
  create: (payload: { name?: string; url: string; provider_id?: string }) =>
    unwrap<EpgSource>(api.post('/epg/sources', payload)),
  sync: (id: string) => unwrap<Record<string, unknown>>(api.post(`/epg/sources/${id}/sync`)),
  remove: (id: string) => unwrap<{ message: string }>(api.delete(`/epg/sources/${id}`)),
  upload: (file: File, name?: string) => {
    const form = new FormData();
    form.append('file', file);
    if (name) form.append('name', name);
    form.append('replace', 'true');
    return unwrap<Record<string, unknown>>(
      api.post('/epg/upload', form, { headers: { 'Content-Type': 'multipart/form-data' } }),
    );
  },
  guide: (params: { hours?: number; channel_id?: string } = {}) =>
    unwrap<Programme[]>(api.get('/epg/guide', { params })),
  programmes: (sourceId: string) => unwrap<Programme[]>(api.get(`/epg/sources/${sourceId}/programmes`)),
};

export const favoritesApi = {
  list: () => unwrap<Favorite[]>(api.get('/favorites')),
  add: (channelId: string) => unwrap<Favorite>(api.post('/favorites', { channel_id: channelId })),
  remove: (channelId: string) => unwrap<{ message: string }>(api.delete(`/favorites/${channelId}`)),
  sync: (channelIds: string[]) =>
    unwrap<Favorite[]>(api.put('/favorites/sync', channelIds.map((channel_id) => ({ channel_id })))),
};

export const historyApi = {
  list: (limit = 50) => unwrap<HistoryEntry[]>(api.get('/history', { params: { limit } })),
  record: (payload: { channel_id: string; position_seconds?: number; duration_seconds?: number; device?: string }) =>
    unwrap<HistoryEntry>(api.post('/history', payload)),
  continueWatching: (limit = 12) =>
    unwrap<HistoryEntry[]>(api.get('/history/continue', { params: { limit } })),
  recent: (limit = 12) => unwrap<HistoryEntry[]>(api.get('/history/recent', { params: { limit } })),
  clear: () => unwrap<{ message: string }>(api.delete('/history')),
};

export const scanApi = {
  start: (payload: { playlist_id?: string; provider_id?: string; probe?: boolean } = { probe: true }) =>
    unwrap<ScanJob>(api.post('/scan', payload)),
  jobs: (limit = 20) => unwrap<ScanJob[]>(api.get('/scan/jobs', { params: { limit } })),
  job: (id: string) => unwrap<ScanJob>(api.get(`/scan/jobs/${id}`)),
  latest: () => unwrap<ScanJob | null>(api.get('/scan/latest')),
};

export const statsApi = {
  dashboard: () => unwrap<DashboardStats>(api.get('/stats/dashboard')),
  activity: (limit = 50) => unwrap<ActivityEntry[]>(api.get('/stats/activity', { params: { limit } })),
};

export const settingsApi = {
  list: () => unwrap<SettingsEntry[]>(api.get('/settings')),
  save: (key: string, value: Record<string, unknown>) => unwrap<SettingsEntry>(api.put('/settings', { key, value })),
  remove: (key: string) => unwrap<{ message: string }>(api.delete(`/settings/${key}`)),
};
