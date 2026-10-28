/** Constantes d'interface partagées. */
export const APP_NAME = 'PrimeTV';
export const APP_TAGLINE = 'Le direct, partout, librement.';

export const NAV_ITEMS = [
  { to: '/', label: 'Tableau de bord', icon: 'LayoutDashboard' },
  { to: '/channels', label: 'Toutes les chaînes', icon: 'Tv' },
  { to: '/channels?category=sport', label: 'Sport', icon: 'Trophy' },
  { to: '/channels?language=ar', label: 'Chaînes arabes', icon: 'Globe2' },
  { to: '/channels?radio=true', label: 'Radios', icon: 'Radio' },
  { to: '/favorites', label: 'Favoris', icon: 'Heart' },
  { to: '/guide', label: 'Guide TV', icon: 'CalendarClock' },
  { to: '/sources', label: 'Sources & playlists', icon: 'FolderDown' },
  { to: '/scan', label: 'Scan & actualisation', icon: 'Radar' },
] as const;

export const SETTINGS_NAV = { to: '/settings', label: 'Réglages', icon: 'Settings' } as const;

export const QUALITY_ORDER = ['8K', '4K', 'FHD', 'HD', 'SD'];

export const CATEGORY_GRADIENTS: Record<string, string> = {
  sport: 'from-emerald-500/25 to-emerald-500/5',
  news: 'from-blue-500/25 to-blue-500/5',
  movies: 'from-purple-500/25 to-purple-500/5',
  kids: 'from-orange-500/25 to-orange-500/5',
  music: 'from-pink-500/25 to-pink-500/5',
  religion: 'from-teal-500/25 to-teal-500/5',
  documentary: 'from-yellow-500/25 to-yellow-500/5',
  entertainment: 'from-violet-500/25 to-violet-500/5',
  local: 'from-slate-500/25 to-slate-500/5',
  culture: 'from-cyan-500/25 to-cyan-500/5',
  adult: 'from-rose-500/25 to-rose-500/5',
};

export const PAGE_SIZE = 24;
