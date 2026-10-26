/** Helpers de formatage (dates, durées, libellés) sans dépendance externe. */

export function formatNumber(value: number | null | undefined): string {
  if (value === null || value === undefined) return '—';
  return new Intl.NumberFormat('fr-FR').format(value);
}

export function formatDateTime(value?: string | null): string {
  if (!value) return '—';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return '—';
  return new Intl.DateTimeFormat('fr-FR', { dateStyle: 'medium', timeStyle: 'short' }).format(date);
}

export function formatTime(value?: string | null): string {
  if (!value) return '—';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return '—';
  return new Intl.DateTimeFormat('fr-FR', { hour: '2-digit', minute: '2-digit' }).format(date);
}

export function relativeTime(value?: string | null): string {
  if (!value) return 'jamais';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return 'jamais';
  const diff = Math.round((date.getTime() - Date.now()) / 1000);
  const units: [Intl.RelativeTimeFormatUnit, number][] = [
    ['second', 60],
    ['minute', 60],
    ['hour', 24],
    ['day', 30],
    ['month', 12],
    ['year', Number.POSITIVE_INFINITY],
  ];
  const formatter = new Intl.RelativeTimeFormat('fr', { numeric: 'auto' });
  let amount = diff;
  for (const [unit, size] of units) {
    if (Math.abs(amount) < size) return formatter.format(Math.round(amount), unit);
    amount /= size;
  }
  return formatDateTime(value);
}

export function formatDuration(seconds?: number | null): string {
  if (!seconds || seconds < 0) return '—';
  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  const remaining = Math.floor(seconds % 60);
  if (hours) return `${hours}h ${String(minutes).padStart(2, '0')}m`;
  if (minutes) return `${minutes}m ${String(remaining).padStart(2, '0')}s`;
  return `${remaining}s`;
}

export const STATUS_LABELS: Record<string, string> = {
  active: 'En ligne',
  offline: 'Hors ligne',
  encrypted: 'Chiffrée',
  unknown: 'Non testée',
  running: 'En cours',
  queued: 'En attente',
  done: 'Terminé',
  failed: 'Échec',
  success: 'Succès',
  error: 'Erreur',
  pending: 'En attente',
};

export const STREAM_TYPE_LABELS: Record<string, string> = {
  hls: 'HLS',
  dash: 'DASH',
  mp4: 'MP4',
  mpegts: 'MPEG-TS',
  audio: 'Radio',
  other: 'Autre',
};

export const ENCRYPTION_LABELS: Record<string, string> = {
  none: 'Libre',
  unknown: 'Non analysé',
  'aes-128': 'AES-128',
  clearkey: 'ClearKey',
  'sample-aes': 'Sample-AES',
  widevine: 'Widevine',
  playready: 'PlayReady',
  fairplay: 'FairPlay',
};

export function initials(name: string): string {
  return name
    .split(/\s+/)
    .slice(0, 2)
    .map((part) => part.charAt(0).toUpperCase())
    .join('');
}

export function channelInitials(name: string): string {
  const cleaned = name.replace(/[^\p{L}\p{N} ]/gu, ' ').trim();
  return initials(cleaned || name);
}

export function clamp(value: number, min: number, max: number): number {
  return Math.min(max, Math.max(min, value));
}
