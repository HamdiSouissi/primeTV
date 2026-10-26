/** Structure principale : sidebar, barre supérieure, contenu et lecteur superposé. */
import { clsx } from 'clsx';
import {
  CalendarClock,
  FolderDown,
  Globe2,
  Heart,
  LayoutDashboard,
  LogOut,
  Menu,
  Moon,
  Radar,
  Radio,
  Search,
  Settings,
  Sun,
  Tv,
  Trophy,
  UserRound,
  X,
} from 'lucide-react';
import { Suspense, lazy, useEffect, useState } from 'react';
import { NavLink, Outlet, useLocation, useNavigate } from 'react-router-dom';
import { useProfiles } from '@/hooks/queries';
import { APP_NAME } from '@/lib/constants';
import { useAuthStore } from '@/store/auth';
import { useUiStore } from '@/store/ui';

// Le lecteur (hls.js + dash.js) est chargé à la demande pour alléger le bundle initial.
const PlayerOverlay = lazy(() =>
  import('@/components/PlayerOverlay').then((module) => ({ default: module.PlayerOverlay })),
);

const ICONS: Record<string, React.ComponentType<{ className?: string }>> = {
  LayoutDashboard,
  Tv,
  Trophy,
  Globe2,
  Radio,
  Heart,
  CalendarClock,
  FolderDown,
  Radar,
  Settings,
};

const NAV = [
  { to: '/', label: 'Tableau de bord', icon: 'LayoutDashboard', end: true },
  { to: '/channels', label: 'Toutes les chaînes', icon: 'Tv', end: true },
  { to: '/channels?category=sport', label: 'Sport', icon: 'Trophy' },
  { to: '/channels?language=ar', label: 'Chaînes arabes', icon: 'Globe2' },
  { to: '/channels?radio=true', label: 'Radios', icon: 'Radio' },
  { to: '/favorites', label: 'Favoris', icon: 'Heart' },
  { to: '/guide', label: 'Guide TV', icon: 'CalendarClock' },
  { to: '/sources', label: 'Sources & playlists', icon: 'FolderDown' },
  { to: '/scan', label: 'Scan & actualisation', icon: 'Radar' },
  { to: '/settings', label: 'Réglages', icon: 'Settings' },
];

export function Layout() {
  const [query, setQuery] = useState('');
  const navigate = useNavigate();
  const location = useLocation();
  const { theme, toggleTheme, sidebarOpen, setSidebarOpen } = useUiStore();
  const { user, profileId, setProfileId, logout } = useAuthStore();
  const { data: profiles } = useProfiles();

  useEffect(() => {
    setSidebarOpen(false);
    setQuery(new URLSearchParams(location.search).get('q') ?? '');
  }, [location.pathname, location.search, setSidebarOpen]);

  const onSearch = (event: React.FormEvent) => {
    event.preventDefault();
    navigate(query.trim() ? `/channels?q=${encodeURIComponent(query.trim())}` : '/channels');
  };

  const onLogout = () => {
    logout();
    navigate('/login');
  };

  return (
    <div className="min-h-screen bg-slate-100 text-slate-800 dark:bg-night-950 dark:bg-mesh-dark dark:text-slate-100">
      {/* Sidebar desktop */}
      <aside className="fixed inset-y-0 left-0 z-40 hidden w-64 flex-col border-r border-slate-200 bg-white/80 px-4 py-5 backdrop-blur-xl dark:border-white/5 dark:bg-night-900/70 lg:flex">
        <Brand />
        <nav className="mt-6 flex-1 space-y-1 overflow-y-auto pr-1">
          {NAV.map((item) => {
            const Icon = ICONS[item.icon] ?? Tv;
            return (
              <NavLink
                key={item.to}
                to={item.to}
                end={item.end}
                className={({ isActive }) => clsx('sidebar-link', isActive && 'sidebar-link-active')}
              >
                <Icon className="h-4 w-4" />
                <span className="truncate">{item.label}</span>
              </NavLink>
            );
          })}
        </nav>
        <div className="mt-4 rounded-xl border border-white/10 bg-gradient-to-br from-brand-600/20 to-accent-500/10 p-3 text-xs text-slate-600 dark:text-slate-300">
          <p className="font-semibold text-slate-800 dark:text-white">100 % open source</p>
          <p className="mt-1 leading-relaxed">FastAPI · React · PostgreSQL · Redis · Docker · Flutter</p>
          <a
            href="/docs"
            target="_blank"
            rel="noreferrer"
            className="mt-2 inline-block font-semibold text-brand-600 hover:underline dark:text-brand-300"
          >
            Documentation API ↗
          </a>
        </div>
      </aside>

      {/* Drawer mobile */}
      {sidebarOpen && (
        <div className="fixed inset-0 z-50 lg:hidden">
          <div className="absolute inset-0 bg-night-950/70" onClick={() => setSidebarOpen(false)} />
          <aside className="absolute inset-y-0 left-0 w-72 animate-fade-up border-r border-white/10 bg-night-900 px-4 py-5">
            <div className="flex items-center justify-between">
              <Brand />
              <button type="button" onClick={() => setSidebarOpen(false)} aria-label="Fermer le menu">
                <X className="h-5 w-5" />
              </button>
            </div>
            <nav className="mt-6 space-y-1 overflow-y-auto">
              {NAV.map((item) => {
                const Icon = ICONS[item.icon] ?? Tv;
                return (
                  <NavLink
                    key={item.to}
                    to={item.to}
                    end={item.end}
                    className={({ isActive }) => clsx('sidebar-link', isActive && 'sidebar-link-active')}
                  >
                    <Icon className="h-4 w-4" />
                    {item.label}
                  </NavLink>
                );
              })}
            </nav>
          </aside>
        </div>
      )}

      <div className="lg:pl-64">
        <header className="sticky top-0 z-30 border-b border-slate-200/70 bg-white/80 backdrop-blur-xl dark:border-white/5 dark:bg-night-900/70">
          <div className="flex items-center gap-3 px-4 py-3 sm:px-6">
            <button
              type="button"
              className="btn-ghost !px-2 !py-2 lg:hidden"
              onClick={() => setSidebarOpen(true)}
              aria-label="Ouvrir le menu"
            >
              <Menu className="h-5 w-5" />
            </button>

            <form onSubmit={onSearch} className="relative flex-1">
              <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
              <input
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                className="input pl-9"
                placeholder="Rechercher une chaîne, une catégorie, une langue…"
                aria-label="Recherche rapide"
              />
            </form>

            <div className="flex items-center gap-2">
              <div className="hidden items-center gap-1.5 rounded-xl border border-slate-200 px-2 py-1.5 dark:border-white/10 md:flex">
                <UserRound className="h-4 w-4 text-slate-400" />
                <select
                  aria-label="Profil actif"
                  className="max-w-[130px] bg-transparent text-xs font-semibold text-slate-700 outline-none dark:text-slate-200"
                  value={profileId ?? ''}
                  onChange={(event) => setProfileId(event.target.value)}
                >
                  {(profiles ?? []).map((profile) => (
                    <option key={profile.id} value={profile.id} className="text-slate-900">
                      {profile.name}
                      {profile.is_kids ? ' (kids)' : ''}
                    </option>
                  ))}
                </select>
              </div>
              <button
                type="button"
                onClick={toggleTheme}
                className="btn-ghost !px-2 !py-2"
                aria-label={theme === 'dark' ? 'Passer en mode clair' : 'Passer en mode sombre'}
              >
                {theme === 'dark' ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
              </button>
              <div className="hidden text-right sm:block">
                <p className="text-xs font-semibold text-slate-800 dark:text-white">{user?.full_name ?? user?.username}</p>
                <p className="text-[11px] text-slate-500 dark:text-slate-400">{user?.role === 'admin' ? 'Administrateur' : 'Utilisateur'}</p>
              </div>
              <button type="button" onClick={onLogout} className="btn-ghost !px-2 !py-2" aria-label="Se déconnecter">
                <LogOut className="h-4 w-4" />
              </button>
            </div>
          </div>
        </header>

        <main className="mx-auto w-full max-w-[1500px] px-4 py-6 sm:px-6">
          <Outlet />
        </main>
      </div>

      <Suspense fallback={null}>
        <PlayerOverlay />
      </Suspense>
    </div>
  );
}

function Brand() {
  return (
    <NavLink to="/" className="flex items-center gap-2.5">
      <span className="relative flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-brand-500 to-accent-500 shadow-glow">
        <Tv className="h-5 w-5 text-white" />
        <span className="absolute -right-0.5 -top-0.5 h-2.5 w-2.5 rounded-full bg-emerald-400 ring-2 ring-white dark:ring-night-900" />
      </span>
      <span>
        <span className="block font-display text-lg font-extrabold leading-none tracking-tight text-slate-900 dark:text-white">
          {APP_NAME}
        </span>
        <span className="text-[10px] font-medium uppercase tracking-[0.18em] text-slate-500 dark:text-slate-400">
          Live · Sport · Arabe
        </span>
      </span>
    </NavLink>
  );
}
