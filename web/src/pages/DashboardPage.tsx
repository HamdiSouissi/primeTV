/** Tableau de bord : indicateurs, priorités sport/arabe, reprise de lecture et activité. */
import { clsx } from 'clsx';
import {
  Activity,
  ArrowRight,
  CalendarClock,
  FolderDown,
  Globe2,
  Heart,
  History,
  Lock,
  PlayCircle,
  Radar,
  Radio,
  Tv,
  Trophy,
  Users,
} from 'lucide-react';
import { Link } from 'react-router-dom';
import { useChannels, useContinueWatching, useDashboard, useFacets } from '@/hooks/queries';
import { CATEGORY_GRADIENTS } from '@/lib/constants';
import { formatNumber, relativeTime, STATUS_LABELS } from '@/lib/format';
import { useAuthStore } from '@/store/auth';
import { useUiStore } from '@/store/ui';
import { ChannelCard } from '@/components/ChannelCard';
import { ChannelGridSkeleton } from '@/components/ChannelGrid';
import { Badge, LoadingBlock, ProgressBar, SectionHeading, StatCard } from '@/components/ui';

function Rail({
  title,
  subtitle,
  icon,
  channels,
  loading,
  href,
}: {
  title: string;
  subtitle: string;
  icon: React.ReactNode;
  channels: Parameters<typeof ChannelCard>[0]['channel'][];
  loading: boolean;
  href: string;
}) {
  return (
    <section>
      <SectionHeading
        title={title}
        subtitle={subtitle}
        action={
          <Link to={href} className="inline-flex items-center gap-1 text-xs font-semibold text-brand-600 hover:underline dark:text-brand-300">
            Tout voir <ArrowRight className="h-3.5 w-3.5" />
          </Link>
        }
      />
      <div className="mb-2 flex items-center gap-2 text-xs text-slate-500 dark:text-slate-400">{icon}</div>
      {loading ? (
        <ChannelGridSkeleton count={4} />
      ) : (
        <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
          {channels.map((channel) => (
            <ChannelCard key={channel.id} channel={channel} compact />
          ))}
        </div>
      )}
    </section>
  );
}

export function DashboardPage() {
  const user = useAuthStore((state) => state.user);
  const openPlayer = useUiStore((state) => state.openPlayer);
  const { data: stats, isLoading } = useDashboard();
  const { data: facets } = useFacets();
  const { data: continueWatching } = useContinueWatching();
  const sport = useChannels({ category: 'sport', page_size: 4 });
  const arabic = useChannels({ language: 'ar', page_size: 4 });

  if (isLoading || !stats) return <LoadingBlock label="Chargement du tableau de bord…" />;

  const categories = [...stats.by_category].sort((a, b) => b.count - a.count).slice(0, 8);
  const maxCategory = Math.max(1, ...categories.map((item) => item.count));
  const scan = stats.last_scan;

  return (
    <div className="space-y-8">
      <header className="surface relative overflow-hidden p-5 sm:p-7">
        <div className="absolute inset-0 bg-mesh-dark opacity-80 dark:opacity-100" />
        <div className="relative flex flex-wrap items-center justify-between gap-4">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-brand-600 dark:text-brand-300">
              Bonjour {user?.full_name?.split(' ')[0] ?? user?.username ?? ''}
            </p>
            <h1 className="mt-1 font-display text-2xl font-extrabold text-slate-900 dark:text-white sm:text-3xl">
              {formatNumber(stats.channels)} chaînes prêtes à être regardées
            </h1>
            <p className="mt-2 max-w-xl text-sm text-slate-600 dark:text-slate-300">
              Sport et chaînes arabes sont remontés en priorité. Lancez un scan pour tester les flux et détecter les
              chaînes chiffrées.
            </p>
            <div className="mt-4 flex flex-wrap gap-2">
              <Link to="/channels" className="btn-primary !py-2">
                <PlayCircle className="h-4 w-4" /> Regarder le direct
              </Link>
              <Link to="/sources" className="btn-soft !py-2">
                <FolderDown className="h-4 w-4" /> Importer une playlist
              </Link>
              <Link to="/scan" className="btn-ghost !py-2">
                <Radar className="h-4 w-4" /> Scanner
              </Link>
            </div>
          </div>
          <div className="grid w-full max-w-xs grid-cols-2 gap-3">
            <div className="rounded-xl border border-white/10 bg-white/5 p-3">
              <p className="text-[11px] uppercase tracking-wide text-slate-500 dark:text-slate-400">Actifs</p>
              <p className="font-display text-xl font-bold text-emerald-500 dark:text-emerald-300">{formatNumber(stats.active_streams)}</p>
            </div>
            <div className="rounded-xl border border-white/10 bg-white/5 p-3">
              <p className="text-[11px] uppercase tracking-wide text-slate-500 dark:text-slate-400">Chiffrés</p>
              <p className="font-display text-xl font-bold text-purple-500 dark:text-purple-300">{formatNumber(stats.encrypted_streams)}</p>
            </div>
            <div className="rounded-xl border border-white/10 bg-white/5 p-3">
              <p className="text-[11px] uppercase tracking-wide text-slate-500 dark:text-slate-400">Bouquets</p>
              <p className="font-display text-xl font-bold text-slate-800 dark:text-white">{formatNumber(stats.bouquets)}</p>
            </div>
            <div className="rounded-xl border border-white/10 bg-white/5 p-3">
              <p className="text-[11px] uppercase tracking-wide text-slate-500 dark:text-slate-400">Favoris</p>
              <p className="font-display text-xl font-bold text-rose-500 dark:text-rose-300">{formatNumber(stats.favorites)}</p>
            </div>
          </div>
        </div>
      </header>

      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <StatCard label="Chaînes" value={formatNumber(stats.channels)} hint={`${formatNumber(stats.radios)} radios`} icon={<Tv className="h-5 w-5" />} />
        <StatCard label="Bouquets" value={formatNumber(stats.bouquets)} hint={`${formatNumber(stats.providers)} fournisseurs`} icon={<FolderDown className="h-5 w-5" />} />
        <StatCard label="Flux actifs" value={formatNumber(stats.active_streams)} hint={`${formatNumber(stats.offline_streams)} hors ligne`} icon={<Activity className="h-5 w-5" />} />
        <StatCard label="EPG" value={formatNumber(stats.epg_programmes)} hint={`${formatNumber(stats.epg_sources)} sources XMLTV`} icon={<CalendarClock className="h-5 w-5" />} />
      </div>

      <div className="grid gap-4 lg:grid-cols-3">
        <section className="surface p-5 lg:col-span-2">
          <SectionHeading title="Répartition par catégorie" subtitle="Classement automatique à l’import" />
          <div className="space-y-2.5">
            {categories.map((category) => (
              <Link key={category.slug} to={`/channels?category=${category.slug}`} className="block">
                <div className="flex items-center gap-3">
                  <span className="w-28 shrink-0 truncate text-xs font-semibold text-slate-600 dark:text-slate-300">{category.name}</span>
                  <div className="h-2 flex-1 overflow-hidden rounded-full bg-slate-200 dark:bg-white/10">
                    <div
                      className={clsx('h-full rounded-full bg-gradient-to-r', CATEGORY_GRADIENTS[category.slug] ?? 'from-brand-500/60 to-brand-500/20')}
                      style={{ width: `${Math.max(6, (category.count / maxCategory) * 100)}%` }}
                    />
                  </div>
                  <span className="w-10 text-right text-xs tabular-nums text-slate-500 dark:text-slate-400">{category.count}</span>
                </div>
              </Link>
            ))}
            {!categories.length && <p className="text-sm text-slate-500">Importez une playlist pour voir les catégories.</p>}
          </div>

          <div className="mt-6 flex flex-wrap gap-2">
            {(facets?.languages ?? []).slice(0, 8).map((language) => (
              <Link key={language.code} to={`/channels?language=${language.code}`} className="chip">
                <span>{language.flag ?? '🌍'}</span> {language.name}
                <span className="rounded-full bg-slate-900/5 px-1.5 text-[10px] dark:bg-white/10">{language.count}</span>
              </Link>
            ))}
          </div>
        </section>

        <section className="surface p-5">
          <SectionHeading title="Historique" subtitle="Reprendre où vous en étiez" />
          <ul className="space-y-2">
            {(continueWatching ?? []).length === 0 && (
              <li className="text-sm text-slate-500 dark:text-slate-400">Aucune lecture récente. Lancez une chaîne pour démarrer.</li>
            )}
            {(continueWatching ?? []).slice(0, 5).map((entry) => (
              <li key={entry.id}>
                <button
                  type="button"
                  onClick={() => openPlayer(entry.channel_id)}
                  className="flex w-full items-center gap-3 rounded-xl border border-transparent p-2 text-left transition hover:border-brand-500/30 hover:bg-brand-500/5"
                >
                  <span className="flex h-9 w-12 shrink-0 items-center justify-center overflow-hidden rounded-lg bg-white/10">
                    {entry.channel?.logo ? (
                      <img src={entry.channel.logo} alt="" className="h-full w-full object-contain p-1" />
                    ) : (
                      <PlayCircle className="h-4 w-4 text-slate-400" />
                    )}
                  </span>
                  <span className="min-w-0 flex-1">
                    <span className="block truncate text-xs font-semibold text-slate-800 dark:text-slate-100">
                      {entry.channel?.name ?? 'Chaîne'}
                    </span>
                    <span className="block text-[11px] text-slate-500">{relativeTime(entry.watched_at)}</span>
                  </span>
                  <History className="h-4 w-4 shrink-0 text-slate-400" />
                </button>
              </li>
            ))}
          </ul>

          <div className="mt-5 rounded-xl border border-white/10 bg-white/5 p-3">
            <p className="flex items-center gap-1.5 text-xs font-semibold text-slate-700 dark:text-slate-200">
              <Radar className="h-3.5 w-3.5" /> Dernier scan
            </p>
            {scan ? (
              <>
                <p className="mt-1 text-[11px] text-slate-500 dark:text-slate-400">
                  {STATUS_LABELS[scan.status] ?? scan.status} · {relativeTime(scan.finished_at ?? scan.started_at)}
                </p>
                <div className="mt-2">
                  <ProgressBar value={scan.total ? (scan.progress / scan.total) * 100 : scan.progress} label={`${scan.active}/${scan.total} actifs`} />
                </div>
              </>
            ) : (
              <p className="mt-1 text-[11px] text-slate-500">Aucun scan exécuté pour l’instant.</p>
            )}
            <Link to="/scan" className="mt-2 inline-flex items-center gap-1 text-[11px] font-semibold text-brand-600 hover:underline dark:text-brand-300">
              Ouvrir le scan <ArrowRight className="h-3 w-3" />
            </Link>
          </div>
        </section>
      </div>

      <Rail
        title="Sport en direct"
        subtitle="Les compétitions et chaînes sportives d’abord"
        icon={<Trophy className="h-3.5 w-3.5 text-emerald-500" />}
        channels={sport.data?.items ?? []}
        loading={sport.isLoading}
        href="/channels?category=sport"
      />
      <Rail
        title="Chaînes arabes"
        subtitle="News, sport, religion et divertissement en arabe"
        icon={<Globe2 className="h-3.5 w-3.5 text-brand-400" />}
        channels={arabic.data?.items ?? []}
        loading={arabic.isLoading}
        href="/channels?language=ar"
      />

      <section className="grid gap-4 lg:grid-cols-2">
        <div className="surface p-5">
          <SectionHeading title="Activité récente" subtitle="Imports, scans et actions" />
          <ul className="space-y-3">
            {stats.recent_activity.slice(0, 8).map((entry) => (
              <li key={entry.id} className="flex items-start gap-3 text-xs">
                <span className="mt-0.5 rounded-lg bg-brand-500/10 p-1.5 text-brand-500 dark:text-brand-300">
                  <Activity className="h-3.5 w-3.5" />
                </span>
                <div>
                  <p className="font-medium text-slate-700 dark:text-slate-200">{entry.message}</p>
                  <p className="text-[11px] text-slate-500">{relativeTime(entry.created_at)}</p>
                </div>
              </li>
            ))}
            {!stats.recent_activity.length && <li className="text-sm text-slate-500">Aucune activité enregistrée.</li>}
          </ul>
        </div>

        <div className="surface p-5">
          <SectionHeading title="État des flux" subtitle="Résultat des derniers tests réseau" />
          <div className="grid grid-cols-2 gap-3">
            {[
              { label: 'En ligne', value: stats.active_streams, tone: 'text-emerald-500' },
              { label: 'Hors ligne', value: stats.offline_streams, tone: 'text-rose-500' },
              { label: 'Chiffrés', value: stats.encrypted_streams, tone: 'text-purple-500' },
              { label: 'DRM', value: stats.drm_streams, tone: 'text-amber-500' },
            ].map((item) => (
              <div key={item.label} className="rounded-xl border border-white/10 bg-white/5 p-3">
                <p className="text-[11px] uppercase tracking-wide text-slate-500 dark:text-slate-400">{item.label}</p>
                <p className={clsx('font-display text-2xl font-bold', item.tone)}>{formatNumber(item.value)}</p>
              </div>
            ))}
          </div>
          <div className="mt-4 flex flex-wrap gap-2 text-[11px] text-slate-500 dark:text-slate-400">
            <Badge tone="info"><Users className="h-3 w-3" /> {stats.providers} fournisseurs</Badge>
            <Badge tone="neutral"><Heart className="h-3 w-3" /> {stats.favorites} favoris</Badge>
            <Badge tone="live"><Radio className="h-3 w-3" /> {stats.radios} radios</Badge>
            <Badge tone="lock"><Lock className="h-3 w-3" /> {stats.encrypted_streams} chiffrées</Badge>
          </div>
        </div>
      </section>
    </div>
  );
}
