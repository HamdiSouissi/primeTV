/** Guide TV issu de l’EPG XMLTV, groupé par chaîne. */
import { CalendarClock, Clock, RefreshCw } from 'lucide-react';
import { useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import type { Programme } from '@/api/types';
import { useChannels, useGuide } from '@/hooks/queries';
import { formatTime } from '@/lib/format';
import { useUiStore } from '@/store/ui';
import { Badge, EmptyState, LoadingBlock, SectionHeading } from '@/components/ui';

const WINDOWS = [6, 12, 24, 48];

export function GuidePage() {
  const [hours, setHours] = useState(24);
  const { data: programmes, isLoading, refetch, isFetching } = useGuide(hours);
  const { data: channelsPage } = useChannels({ page_size: 200, sort: 'priority' });
  const openPlayer = useUiStore((state) => state.openPlayer);

  const channelNames = useMemo(() => {
    const map = new Map<string, { name: string; logo?: string | null }>();
    for (const channel of channelsPage?.items ?? []) {
      map.set(channel.id, { name: channel.name, logo: channel.logo });
    }
    return map;
  }, [channelsPage]);

  const grouped = useMemo(() => {
    const map = new Map<string, Programme[]>();
    for (const programme of programmes ?? []) {
      const key = programme.channel_id ?? programme.xmltv_id;
      const list = map.get(key) ?? [];
      list.push(programme);
      map.set(key, list);
    }
    return [...map.entries()].sort((a, b) => {
      const first = a[1]?.[0]?.start_at ?? '';
      const second = b[1]?.[0]?.start_at ?? '';
      return first.localeCompare(second);
    });
  }, [programmes]);

  const now = Date.now();

  return (
    <div className="space-y-5">
      <SectionHeading
        title="Guide TV"
        subtitle="Programmes issus de vos sources XMLTV, associés automatiquement aux chaînes."
        action={
          <div className="flex flex-wrap items-center gap-2">
            {WINDOWS.map((window) => (
              <button key={window} type="button" onClick={() => setHours(window)} className={`chip ${hours === window ? 'chip-active' : ''}`}>
                {window} h
              </button>
            ))}
            <button type="button" className="btn-soft !py-2" onClick={() => void refetch()}>
              <RefreshCw className={`h-4 w-4 ${isFetching ? 'animate-spin' : ''}`} /> Actualiser
            </button>
          </div>
        }
      />

      {isLoading ? (
        <LoadingBlock label="Chargement du guide…" />
      ) : grouped.length ? (
        <div className="space-y-3">
          {grouped.map(([channelId, list]) => {
            const meta = channelNames.get(channelId);
            return (
              <section key={channelId} className="surface overflow-hidden">
                <div className="flex items-center gap-3 border-b border-white/10 px-4 py-3">
                  <div className="flex h-9 w-12 items-center justify-center overflow-hidden rounded-lg bg-white/10">
                    {meta?.logo ? <img src={meta.logo} alt="" className="h-full w-full object-contain p-1" /> : <CalendarClock className="h-4 w-4 text-slate-400" />}
                  </div>
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm font-semibold text-slate-800 dark:text-slate-100">
                      {meta?.name ?? list[0]?.xmltv_id ?? 'Chaîne'}
                    </p>
                    <p className="text-[11px] text-slate-500">{list.length} programmes sur {hours} h</p>
                  </div>
                  {meta && (
                    <button type="button" className="btn-soft !px-3 !py-1.5 !text-xs" onClick={() => openPlayer(channelId)}>
                      Regarder
                    </button>
                  )}
                </div>
                <ul className="divide-y divide-white/5">
                  {list.slice(0, 30).map((programme) => {
                    const start = new Date(programme.start_at).getTime();
                    const stop = new Date(programme.stop_at).getTime();
                    const live = start <= now && stop > now;
                    return (
                      <li key={programme.id} className={`flex items-start gap-3 px-4 py-2.5 text-sm ${live ? 'bg-brand-500/5' : ''}`}>
                        <span className="w-24 shrink-0 text-xs font-semibold tabular-nums text-slate-500 dark:text-slate-400">
                          {formatTime(programme.start_at)} – {formatTime(programme.stop_at)}
                        </span>
                        <div className="min-w-0 flex-1">
                          <p className="truncate font-medium text-slate-800 dark:text-slate-100" dir="auto">
                            {programme.title}
                          </p>
                          {programme.description && <p className="line-clamp-1 text-xs text-slate-500">{programme.description}</p>}
                        </div>
                        {live && (
                          <Badge tone="live">
                            <Clock className="h-3 w-3" /> En cours
                          </Badge>
                        )}
                        {programme.category && <Badge tone="neutral">{programme.category}</Badge>}
                      </li>
                    );
                  })}
                </ul>
              </section>
            );
          })}
        </div>
      ) : (
        <EmptyState
          icon={<CalendarClock />}
          title="Aucun programme EPG"
          description="Ajoutez une source XMLTV dans « Sources & playlists » puis synchronisez-la pour enrichir le guide."
          action={
            <Link to="/sources" className="btn-primary">
              Ajouter un EPG
            </Link>
          }
        />
      )}
    </div>
  );
}
