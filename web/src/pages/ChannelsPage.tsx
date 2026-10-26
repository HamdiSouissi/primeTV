/** Catalogue : recherche, filtres, tri et pagination. */
import { clsx } from 'clsx';
import { Filter, LayoutGrid, Lock, Radio, RefreshCw, Search, SlidersHorizontal, Sparkles } from 'lucide-react';
import { useEffect, useMemo, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import type { ChannelQuery } from '@/api/types';
import { useChannels, useFacets } from '@/hooks/queries';
import { PAGE_SIZE } from '@/lib/constants';
import { useDebounce } from '@/lib/useDebounce';
import { ChannelGrid } from '@/components/ChannelGrid';
import { Badge, EmptyState, Toggle } from '@/components/ui';

const SORTS: { value: NonNullable<ChannelQuery['sort']>; label: string }[] = [
  { value: 'priority', label: 'Priorité (sport & arabe)' },
  { value: 'name', label: 'Nom (A→Z)' },
  { value: 'last_checked_at', label: 'Dernier test' },
  { value: 'created_at', label: 'Ajout récent' },
];

export function ChannelsPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const [search, setSearch] = useState(searchParams.get('q') ?? '');
  const debouncedSearch = useDebounce(search, 350);
  const [page, setPage] = useState(1);
  const [sort, setSort] = useState<NonNullable<ChannelQuery['sort']>>(
    (searchParams.get('sort') as NonNullable<ChannelQuery['sort']> | null) ?? 'priority',
  );
  const [encryptedOnly, setEncryptedOnly] = useState(false);
  const [showFilters, setShowFilters] = useState(false);
  const { data: facets } = useFacets();

  const category = searchParams.get('category') ?? undefined;
  const language = searchParams.get('language') ?? undefined;
  const bouquet = searchParams.get('bouquet') ?? undefined;
  const radio = searchParams.get('radio') === 'true' ? true : undefined;

  useEffect(() => {
    setSearch(searchParams.get('q') ?? '');
    setPage(1);
  }, [searchParams]);

  const query: ChannelQuery = useMemo(
    () => ({
      q: debouncedSearch.trim() || undefined,
      category,
      language,
      bouquet,
      radio,
      encrypted: encryptedOnly || undefined,
      sort,
      page,
      page_size: PAGE_SIZE,
    }),
    [debouncedSearch, category, language, bouquet, radio, encryptedOnly, sort, page],
  );

  const { data, isLoading, isFetching, refetch } = useChannels(query);

  const setFilter = (key: string, value?: string) => {
    const next = new URLSearchParams(searchParams);
    if (value === undefined) next.delete(key);
    else next.set(key, value);
    next.delete('page');
    setSearchParams(next);
    setPage(1);
  };

  const activeFilters = [
    category && { key: 'category', label: facets?.categories.find((item) => item.slug === category)?.name ?? category },
    language && { key: 'language', label: facets?.languages.find((item) => item.code === language)?.name ?? language },
    bouquet && { key: 'bouquet', label: facets?.bouquets.find((item) => item.id === bouquet)?.name ?? 'Bouquet' },
    radio && { key: 'radio', label: 'Radios' },
    encryptedOnly && { key: 'encrypted', label: 'Chiffrées' },
  ].filter(Boolean) as { key: string; label: string }[];

  return (
    <div className="space-y-5">
      <header className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="font-display text-2xl font-extrabold text-slate-900 dark:text-white">Toutes les chaînes</h1>
          <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
            {data ? `${data.total} chaînes` : 'Chargement…'} · tri par défaut : sport et arabe en tête
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button type="button" className="btn-soft !py-2" onClick={() => void refetch()} aria-label="Actualiser">
            <RefreshCw className={clsx('h-4 w-4', isFetching && 'animate-spin')} /> Actualiser
          </button>
          <Link to="/sources" className="btn-primary !py-2">
            <Sparkles className="h-4 w-4" /> Importer
          </Link>
        </div>
      </header>

      <div className="surface space-y-3 p-4">
        <div className="flex flex-col gap-3 sm:flex-row">
          <div className="relative flex-1">
            {search ? (
              <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
            ) : (
              <Filter className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
            )}
            <input
              className="input pl-9"
              placeholder="Nom de chaîne, groupe, identifiant TVG…"
              value={search}
              onChange={(event) => {
                setSearch(event.target.value);
                setPage(1);
              }}
              aria-label="Rechercher une chaîne"
            />
          </div>
          <div className="flex gap-2">
            <select className="input sm:w-56" value={sort} onChange={(event) => setSort(event.target.value as NonNullable<ChannelQuery['sort']>)} aria-label="Tri">
              {SORTS.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
            <button
              type="button"
              className={clsx('btn-soft !py-2', showFilters && '!border-brand-500/50 !text-brand-500')}
              onClick={() => setShowFilters((value) => !value)}
            >
              <SlidersHorizontal className="h-4 w-4" /> Filtres
            </button>
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <button type="button" onClick={() => setSearchParams(new URLSearchParams())} className={clsx('chip', !activeFilters.length && 'chip-active')}>
            <LayoutGrid className="h-3.5 w-3.5" /> Tout
          </button>
          {(facets?.categories ?? []).slice(0, 9).map((item) => (
            <button
              key={item.slug}
              type="button"
              onClick={() => setFilter('category', category === item.slug ? undefined : item.slug)}
              className={clsx('chip', category === item.slug && 'chip-active')}
            >
              {item.name}
              <span className="rounded-full bg-black/5 px-1.5 text-[10px] dark:bg-white/10">{item.count}</span>
            </button>
          ))}
          <button
            type="button"
            onClick={() => setFilter('radio', radio ? undefined : 'true')}
            className={clsx('chip', radio && 'chip-active')}
          >
            <Radio className="h-3.5 w-3.5" /> Radios
          </button>
        </div>

        {showFilters && (
          <div className="grid gap-4 border-t border-white/10 pt-3 sm:grid-cols-2 lg:grid-cols-3">
            <div>
              <p className="label">Langues</p>
              <div className="flex flex-wrap gap-1.5">
                {(facets?.languages ?? []).map((item) => (
                  <button
                    key={item.code}
                    type="button"
                    onClick={() => setFilter('language', language === item.code ? undefined : item.code)}
                    className={clsx('chip !px-2.5 !py-1', language === item.code && 'chip-active')}
                  >
                    {item.flag} {item.name}
                  </button>
                ))}
              </div>
            </div>
            <div>
              <p className="label">Bouquets</p>
              <div className="flex flex-wrap gap-1.5">
                {(facets?.bouquets ?? []).slice(0, 12).map((item) => (
                  <button
                    key={item.id}
                    type="button"
                    onClick={() => setFilter('bouquet', bouquet === item.id ? undefined : item.id)}
                    className={clsx('chip !px-2.5 !py-1', bouquet === item.id && 'chip-active')}
                  >
                    {item.name}
                  </button>
                ))}
                {!facets?.bouquets.length && <span className="text-xs text-slate-500">Aucun bouquet.</span>}
              </div>
            </div>
            <div className="space-y-1">
              <Toggle
                checked={encryptedOnly}
                onChange={(value) => {
                  setEncryptedOnly(value);
                  setPage(1);
                }}
                label="Chaînes chiffrées uniquement"
                description="AES-128, ClearKey et DRM signalés par le scan"
              />
              <div className="flex flex-wrap gap-1.5 pt-1">
                <Badge tone="lock">
                  <Lock className="h-3 w-3" /> {facets?.totals.encrypted ?? 0} chiffrées
                </Badge>
                <Badge tone="live">{facets?.totals.active ?? 0} actives</Badge>
              </div>
            </div>
          </div>
        )}
      </div>

      {activeFilters.length > 0 && (
        <div className="flex flex-wrap items-center gap-2 text-xs text-slate-500 dark:text-slate-400">
          Filtres actifs :
          {activeFilters.map((item) => (
            <button
              key={item.key}
              type="button"
              className="chip !py-1"
              onClick={() => {
                if (item.key === 'encrypted') setEncryptedOnly(false);
                else setFilter(item.key);
              }}
            >
              {item.label} ✕
            </button>
          ))}
        </div>
      )}

      <ChannelGrid
        channels={data?.items ?? []}
        isLoading={isLoading}
        action={
          <Link to="/sources" className="btn-primary">
            Importer une playlist
          </Link>
        }
      />

      {data && data.pages > 1 && (
        <nav className="flex flex-wrap items-center justify-center gap-2 pt-2" aria-label="Pagination">
          <button type="button" className="btn-soft !py-2" disabled={page <= 1} onClick={() => setPage((value) => value - 1)}>
            Précédent
          </button>
          {Array.from({ length: Math.min(7, data.pages) }).map((_, index) => {
            const start = Math.max(1, Math.min(page - 3, data.pages - 6));
            const pageNumber = Math.max(1, start + index);
            if (pageNumber > data.pages) return null;
            return (
              <button
                key={pageNumber}
                type="button"
                onClick={() => setPage(pageNumber)}
                className={clsx('btn !px-3 !py-2', pageNumber === page ? 'btn-primary' : 'btn-soft')}
                aria-current={pageNumber === page ? 'page' : undefined}
              >
                {pageNumber}
              </button>
            );
          })}
          <button type="button" className="btn-soft !py-2" disabled={page >= data.pages} onClick={() => setPage((value) => value + 1)}>
            Suivant
          </button>
        </nav>
      )}

      {!isLoading && !data?.items.length && (
        <EmptyState
          icon={<Search />}
          title="Aucun résultat"
          description="Essayez un autre mot-clé, retirez des filtres ou importez une nouvelle playlist."
          action={
            <Link to="/sources" className="btn-primary">
              Importer une playlist
            </Link>
          }
        />
      )}
    </div>
  );
}
