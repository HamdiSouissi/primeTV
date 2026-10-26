/** Types partagés avec l'API PrimeTV (miroir des schémas Pydantic). */

export type Role = 'user' | 'admin';
export type StreamType = 'hls' | 'dash' | 'mp4' | 'mpegts' | 'audio' | 'other';
export type ChannelStatus = 'active' | 'offline' | 'encrypted' | 'unknown';
export type EncryptionType =
  | 'none'
  | 'unknown'
  | 'aes-128'
  | 'clearkey'
  | 'sample-aes'
  | 'widevine'
  | 'playready'
  | 'fairplay';

export interface User {
  id: string;
  email: string;
  username: string;
  full_name?: string | null;
  role: Role;
  is_active: boolean;
  last_login_at?: string | null;
  created_at?: string | null;
}

export interface Profile {
  id: string;
  name: string;
  avatar?: string | null;
  is_kids: boolean;
  is_default: boolean;
  language: string;
  preferences: Record<string, unknown>;
  has_pin?: boolean;
  created_at?: string | null;
}

export interface Tokens {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
  user: User;
}

export interface Category {
  id: string;
  name: string;
  slug: string;
  icon?: string | null;
  color?: string | null;
  position: number;
}

export interface Language {
  id: string;
  code: string;
  name: string;
  native_name?: string | null;
  flag?: string | null;
  position: number;
}

export interface Bouquet {
  id: string;
  name: string;
  slug: string;
  description?: string | null;
  provider_id?: string | null;
  is_public: boolean;
}

export interface Channel {
  id: string;
  name: string;
  logo?: string | null;
  stream_type: StreamType;
  group_title?: string | null;
  country?: string | null;
  quality?: string | null;
  is_radio: boolean;
  is_encrypted: boolean;
  encryption: EncryptionType;
  drm_systems: string[];
  status: ChannelStatus;
  priority: number;
  tvg_id?: string | null;
  epg_channel_id?: string | null;
  category?: Category | null;
  language?: Language | null;
  bouquets: Bouquet[];
  last_checked_at?: string | null;
  is_favorite: boolean;
  stream_url?: string;
  provider_id?: string | null;
  playlist_id?: string | null;
  http_status?: number | null;
  extras?: Record<string, unknown>;
  created_at?: string | null;
  updated_at?: string | null;
}

export interface Variant {
  label: string;
  bandwidth: number;
  resolution?: string | null;
  codecs?: string | null;
  url?: string | null;
}

export interface Playback {
  channel_id: string;
  url: string;
  direct_url?: string | null;
  stream_type: StreamType;
  is_encrypted: boolean;
  encryption: EncryptionType;
  drm_systems: string[];
  variants: Variant[];
  subtitles: string[];
  audio_tracks: string[];
  has_keys: boolean;
  key_system?: string | null;
  clearkey_license?: { keys: { kty: string; kid: string; k: string }[]; type: string } | null;
  message?: string | null;
}

export interface Page<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
}

export interface Provider {
  id: string;
  name: string;
  kind: 'm3u' | 'xtream' | 'hls' | 'dash';
  base_url?: string | null;
  username?: string | null;
  has_password: boolean;
  epg_url?: string | null;
  notes?: string | null;
  is_active: boolean;
  channel_count: number;
  playlist_count: number;
  created_at?: string | null;
  updated_at?: string | null;
}

export interface Playlist {
  id: string;
  name: string;
  source_type: 'url' | 'file' | 'text' | 'xtream' | 'hls' | 'dash';
  url?: string | null;
  file_name?: string | null;
  provider_id?: string | null;
  channel_count: number;
  is_active: boolean;
  auto_sync: boolean;
  last_sync_at?: string | null;
  last_error?: string | null;
  created_at?: string | null;
  updated_at?: string | null;
}

export interface ImportResult {
  playlist?: Playlist | null;
  total: number;
  created: number;
  updated: number;
  skipped: number;
  radios: number;
  encrypted: number;
  categories: Record<string, number>;
  warnings: string[];
  epg_urls: string[];
  epg_sources: string[];
}

export interface EpgSource {
  id: string;
  name: string;
  url?: string | null;
  file_name?: string | null;
  provider_id?: string | null;
  programme_count: number;
  status: string;
  last_error?: string | null;
  last_sync_at?: string | null;
  created_at?: string | null;
}

export interface Programme {
  id: string;
  xmltv_id: string;
  channel_id?: string | null;
  title: string;
  subtitle?: string | null;
  description?: string | null;
  category?: string | null;
  icon?: string | null;
  start_at: string;
  stop_at: string;
}

export interface NowNext {
  current: (Programme & { progress?: number }) | null;
  next: Programme | null;
}

export interface Favorite {
  id: string;
  channel_id: string;
  position: number;
  created_at?: string | null;
  channel?: Channel | null;
}

export interface HistoryEntry {
  id: string;
  channel_id: string;
  position_seconds: number;
  duration_seconds?: number | null;
  device?: string | null;
  watched_at: string;
  channel?: Channel | null;
}

export interface ScanJob {
  id: string;
  status: 'queued' | 'running' | 'done' | 'failed';
  progress: number;
  total: number;
  imported: number;
  updated: number;
  active: number;
  offline: number;
  encrypted: number;
  drm_protected: number;
  probe: boolean;
  error?: string | null;
  playlist_id?: string | null;
  provider_id?: string | null;
  started_at?: string | null;
  finished_at?: string | null;
  created_at?: string | null;
  logs: string[];
}

export interface ActivityEntry {
  id: string;
  action: string;
  message: string;
  level: string;
  context: Record<string, unknown>;
  created_at?: string | null;
}

export interface DashboardStats {
  channels: number;
  radios: number;
  bouquets: number;
  providers: number;
  playlists: number;
  active_streams: number;
  offline_streams: number;
  encrypted_streams: number;
  drm_streams: number;
  favorites: number;
  epg_sources: number;
  epg_programmes: number;
  by_category: { name: string; slug: string; color?: string | null; count: number }[];
  by_language: { name: string; code: string; flag?: string | null; count: number }[];
  by_stream_type: { type: string; count: number }[];
  by_status: { status: string; count: number }[];
  recent_activity: ActivityEntry[];
  history: HistoryEntry[];
  last_scan?: ScanJob | null;
}

export interface Facets {
  categories: { slug: string; name: string; color?: string | null; icon?: string | null; count: number }[];
  languages: { code: string; name: string; flag?: string | null; count: number }[];
  bouquets: { id: string; name: string; count: number }[];
  totals: { channels: number; radios: number; encrypted: number; active: number; favorites: number };
}

export interface PublicConfig {
  app_name: string;
  version: string;
  environment: string;
  allow_registration: boolean;
  categories: { slug: string; name: string; icon: string; color: string; position: number }[];
  languages: { code: string; name: string; native_name: string; flag: string; position: number }[];
  quality_levels: string[];
  stream_types: string[];
  encryption_types: string[];
}

export interface ChannelQuery {
  q?: string;
  category?: string;
  language?: string;
  bouquet?: string;
  provider?: string;
  playlist?: string;
  stream_type?: string;
  status?: string;
  encrypted?: boolean;
  radio?: boolean;
  favorites_only?: boolean;
  sort?: 'priority' | 'name' | 'created_at' | 'updated_at' | 'quality' | 'status' | 'last_checked_at';
  order?: 'asc' | 'desc';
  page?: number;
  page_size?: number;
}

export interface SettingsEntry {
  key: string;
  value: Record<string, unknown>;
  updated_at?: string | null;
}
