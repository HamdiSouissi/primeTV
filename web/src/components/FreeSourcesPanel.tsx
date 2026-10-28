/** Panneau « sources libres & légales » : import en un clic depuis Sources → Playlists. */
import { clsx } from 'clsx';
import { Info, Plus, ShieldCheck } from 'lucide-react';
import { useState } from 'react';
import { playlistsApi } from '@/api/endpoints';
import type { ImportResult } from '@/api/types';
import { FREE_SOURCE_GROUPS, type FreeSource, sourcesByGroup } from '@/lib/freeSources';
import { apiErrorMessage } from '@/api/client';
import { toast } from '@/store/toast';

interface FreeSourcesPanelProps {
  /** Appelé après un import réussi (résumé + rafraîchissement des requêtes). */
  onImported: (result: ImportResult) => void;
}

/**
 * Propose des playlists publiques maintenues par des projets open source
 * (iptv-org, Free-TV). Aucune liste piratée : voir `docs/FREE_SOURCES.md`.
 */
export function FreeSourcesPanel({ onImported }: FreeSourcesPanelProps) {
  const [group, setGroup] = useState<string>('Actualités');
  const [pending, setPending] = useState<string | null>(null);

  const visible = sourcesByGroup(group as never);

  const importSource = async (source: FreeSource) => {
    setPending(source.id);
    try {
      const result = await playlistsApi.importUrl({ name: `${source.name} (libre)`, url: source.url });
      onImported(result);
    } catch (error) {
      toast.error(apiErrorMessage(error, 'Import impossible'));
    } finally {
      setPending(null);
    }
  };

  return (
    <section className="surface overflow-hidden">
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-white/10 px-4 py-3">
        <h2 className="flex items-center gap-2 font-display text-sm font-semibold">
          <ShieldCheck className="h-4 w-4 text-emerald-400" />
          Sources libres prêtes à l’emploi
        </h2>
        <span className="text-[11px] text-slate-500 dark:text-slate-400">
          Chaînes publiques & projets open source uniquement
        </span>
      </div>

      <div className="flex flex-wrap gap-2 px-4 py-3">
        {FREE_SOURCE_GROUPS.map((item) => (
          <button
            key={item}
            type="button"
            onClick={() => setGroup(item)}
            className={clsx('chip', group === item && 'chip-active')}
          >
            {item}
          </button>
        ))}
      </div>

      <ul className="grid gap-2 px-4 pb-4 sm:grid-cols-2 xl:grid-cols-3">
        {visible.map((source) => (
          <li
            key={source.id}
            className="flex flex-col gap-2 rounded-xl border border-slate-200 bg-white/60 p-3 transition hover:border-brand-300 dark:border-white/10 dark:bg-white/[0.03] dark:hover:border-brand-500/50"
          >
            <div className="flex items-start gap-2">
              <span aria-hidden className="text-lg leading-none">
                {source.emoji}
              </span>
              <div className="min-w-0 flex-1">
                <p className="truncate text-sm font-semibold text-slate-800 dark:text-slate-100">{source.name}</p>
                <p className="text-[11px] text-slate-500 dark:text-slate-400">
                  {source.kind} · {source.channels} chaînes
                </p>
              </div>
            </div>
            <p className="line-clamp-2 text-xs leading-relaxed text-slate-600 dark:text-slate-400">
              {source.description}
            </p>
            <button
              type="button"
              className="btn-soft mt-auto !py-1.5 !text-xs"
              onClick={() => void importSource(source)}
              disabled={pending !== null}
              aria-label={`Importer ${source.name}`}
            >
              <Plus className="h-3.5 w-3.5" />
              {pending === source.id ? 'Import…' : 'Importer'}
            </button>
          </li>
        ))}
      </ul>

      <p className="flex items-start gap-2 border-t border-white/10 px-4 py-3 text-[11px] leading-relaxed text-slate-500 dark:text-slate-400">
        <Info className="mt-0.5 h-3.5 w-3.5 shrink-0" />
        <span>
          Ces listes ne contiennent que des flux publics (chaînes publiques, FAST, web TV) : PrimeTV n’héberge
          aucun flux et ne contourne aucun DRM. Après l’import, lancez un <strong>scan</strong> pour vérifier la
          disponibilité, et associez un EPG (onglet EPG XMLTV) pour le guide TV.
        </span>
      </p>
    </section>
  );
}
