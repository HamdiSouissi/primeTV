/** Carte de chaîne : logo, badges, favori et lecture au clic. */
import { clsx } from 'clsx';
import { Heart, Lock, Play, Radio, Signal, SignalHigh, SignalLow, Zap } from 'lucide-react';
import { useState } from 'react';
import type { Channel } from '@/api/types';
import { channelInitials, ENCRYPTION_LABELS, STATUS_LABELS, STREAM_TYPE_LABELS } from '@/lib/format';
import { useToggleFavorite } from '@/hooks/queries';
import { useUiStore } from '@/store/ui';
import { Badge } from '@/components/ui';

function qualityIcon(quality?: string | null) {
  if (quality === '4K' || quality === '8K' || quality === 'FHD') return <SignalHigh className="h-3 w-3" />;
  if (quality === 'HD') return <Signal className="h-3 w-3" />;
  return <SignalLow className="h-3 w-3" />;
}

export function ChannelCard({ channel, compact = false }: { channel: Channel; compact?: boolean }) {
  const openPlayer = useUiStore((state) => state.openPlayer);
  const toggleFavorite = useToggleFavorite();
  const [logoError, setLogoError] = useState(false);
  const accent = channel.category?.color ?? '#3382fb';

  const onFavorite = (event: React.MouseEvent) => {
    event.stopPropagation();
    toggleFavorite.mutate({ channelId: channel.id, isFavorite: channel.is_favorite });
  };

  return (
    <article
      className={clsx(
        'group surface relative cursor-pointer overflow-hidden p-3 card-hover focus-within:ring-2 focus-within:ring-brand-400',
        compact && 'p-2.5',
      )}
      onClick={() => openPlayer(channel.id)}
      role="button"
      tabIndex={0}
      onKeyDown={(event) => {
        if (event.key === 'Enter' || event.key === ' ') {
          event.preventDefault();
          openPlayer(channel.id);
        }
      }}
      aria-label={`Lire ${channel.name}`}
    >
      <div
        className="pointer-events-none absolute inset-0 opacity-60"
        style={{ background: `radial-gradient(circle at 15% 0%, ${accent}22, transparent 55%)` }}
      />
      <div className="relative flex items-center gap-3">
        <div
          className={clsx(
            'relative flex shrink-0 items-center justify-center overflow-hidden rounded-xl bg-white/90 ring-1 ring-black/5 dark:bg-night-800',
            compact ? 'h-12 w-16' : 'h-14 w-20',
          )}
        >
          {channel.logo && !logoError ? (
            <img
              src={channel.logo}
              alt=""
              loading="lazy"
              className="h-full w-full object-contain p-1.5"
              onError={() => setLogoError(true)}
            />
          ) : (
            <span className="font-display text-sm font-bold text-slate-500 dark:text-slate-300">
              {channelInitials(channel.name)}
            </span>
          )}
          <span className="absolute inset-0 flex items-center justify-center bg-night-950/60 opacity-0 transition group-hover:opacity-100">
            <Play className="h-5 w-5 fill-white text-white" />
          </span>
        </div>

        <div className="min-w-0 flex-1">
          <div className="flex items-start gap-2">
            <h3 className="min-w-0 flex-1 truncate text-sm font-semibold text-slate-900 dark:text-white" dir="auto">
              {channel.name}
            </h3>
            <button
              type="button"
              aria-label={channel.is_favorite ? 'Retirer des favoris' : 'Ajouter aux favoris'}
              aria-pressed={channel.is_favorite}
              onClick={onFavorite}
              className={clsx(
                'rounded-full p-1 transition hover:scale-110',
                channel.is_favorite ? 'text-rose-500' : 'text-slate-400 hover:text-rose-400',
              )}
            >
              <Heart className={clsx('h-4 w-4', channel.is_favorite && 'fill-current')} />
            </button>
          </div>

          <p className="mt-0.5 truncate text-xs text-slate-500 dark:text-slate-400" dir="auto">
            {channel.category?.name ?? 'Non classée'}
            {channel.language ? ` · ${channel.language.flag ?? ''} ${channel.language.name}` : ''}
          </p>

          <div className="mt-2 flex flex-wrap items-center gap-1.5">
            {channel.quality && (
              <Badge tone="info">
                {qualityIcon(channel.quality)}
                {channel.quality}
              </Badge>
            )}
            <Badge tone="neutral">{STREAM_TYPE_LABELS[channel.stream_type] ?? channel.stream_type}</Badge>
            {channel.is_radio && (
              <Badge tone="info">
                <Radio className="h-3 w-3" /> Radio
              </Badge>
            )}
            {channel.is_encrypted && (
              <Badge tone="lock" className="uppercase">
                <Lock className="h-3 w-3" />
                {ENCRYPTION_LABELS[channel.encryption] ?? channel.encryption}
              </Badge>
            )}
            {channel.status === 'active' && (
              <Badge tone="live">
                <Zap className="h-3 w-3" /> En ligne
              </Badge>
            )}
            {channel.status === 'offline' && <Badge tone="danger">Hors ligne</Badge>}
            {channel.status === 'unknown' && <Badge tone="warning">{STATUS_LABELS.unknown}</Badge>}
          </div>
        </div>
      </div>
    </article>
  );
}
