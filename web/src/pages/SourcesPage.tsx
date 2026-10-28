/** Sources : playlists M3U/Xtream, fournisseurs et EPG XMLTV. */
import { clsx } from 'clsx';
import {
  CalendarClock,
  CloudDownload,
  FileUp,
  FolderDown,
  Link2,
  Plus,
  RefreshCw,
  Server,
  Trash2,
  Upload,
} from 'lucide-react';
import { useRef, useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { apiErrorMessage } from '@/api/client';
import { epgApi, playlistsApi, providersApi } from '@/api/endpoints';
import type { ImportResult } from '@/api/types';
import { useEpgSources, usePlaylists, useProviders } from '@/hooks/queries';
import { formatDateTime, relativeTime, STATUS_LABELS } from '@/lib/format';
import { toast } from '@/store/toast';
import { Badge, EmptyState, LoadingBlock, Modal, SectionHeading } from '@/components/ui';
import { FreeSourcesPanel } from '@/components/FreeSourcesPanel';
import { FREE_EPG_SOURCES } from '@/lib/freeSources';

type Tab = 'playlists' | 'providers' | 'epg';
type ImportMode = 'url' | 'file' | 'xtream' | 'text';

const TABS: { id: Tab; label: string; icon: React.ReactNode }[] = [
  { id: 'playlists', label: 'Playlists', icon: <CloudDownload className="h-4 w-4" /> },
  { id: 'providers', label: 'Fournisseurs', icon: <Server className="h-4 w-4" /> },
  { id: 'epg', label: 'EPG XMLTV', icon: <CalendarClock className="h-4 w-4" /> },
];

function ImportSummary({ result }: { result: ImportResult }) {
  return (
    <div className="rounded-xl border border-emerald-500/30 bg-emerald-500/10 p-3 text-xs text-emerald-700 dark:text-emerald-200">
      <p className="font-semibold">
        {result.created} ajoutées · {result.updated} mises à jour · {result.radios} radios · {result.encrypted} chiffrées
      </p>
      {Object.keys(result.categories).length > 0 && (
        <p className="mt-1 text-emerald-600/90 dark:text-emerald-300/90">
          Catégories :{' '}
          {Object.entries(result.categories)
            .map(([slug, count]) => `${slug} (${count})`)
            .join(', ')}
        </p>
      )}
      {result.epg_urls.length > 0 && (
        <p className="mt-1">EPG détecté : {result.epg_urls.join(', ')} — synchronisez l’onglet EPG.</p>
      )}
      {result.warnings.map((warning) => (
        <p key={warning} className="mt-1 text-amber-600 dark:text-amber-300">
          ⚠ {warning}
        </p>
      ))}
    </div>
  );
}

export function SourcesPage() {
  const [tab, setTab] = useState<Tab>('playlists');
  const [importOpen, setImportOpen] = useState(false);
  const [providerOpen, setProviderOpen] = useState(false);
  const [epgOpen, setEpgOpen] = useState(false);
  const [mode, setMode] = useState<ImportMode>('url');
  const [lastResult, setLastResult] = useState<ImportResult | null>(null);
  const queryClient = useQueryClient();

  const playlists = usePlaylists();
  const providers = useProviders();
  const epgSources = useEpgSources();

  const [playlistForm, setPlaylistForm] = useState({ name: '', url: '' });
  const [textForm, setTextForm] = useState({ name: '', content: '' });
  const [xtreamForm, setXtreamForm] = useState({ name: '', base_url: '', username: '', password: '' });
  const [providerForm, setProviderForm] = useState({ name: '', kind: 'm3u', base_url: '', username: '', password: '', notes: '' });
  const [epgForm, setEpgForm] = useState({ name: '', url: '' });
  const fileRef = useRef<HTMLInputElement | null>(null);

  const invalidateAll = () => {
    for (const key of [['playlists'], ['providers'], ['epg-sources'], ['dashboard'], ['facets'], ['channels']]) {
      void queryClient.invalidateQueries({ queryKey: key });
    }
  };

  const onImported = (result: ImportResult) => {
    setLastResult(result);
    toast.success(`Import terminé : ${result.created} chaînes ajoutées`);
    invalidateAll();
  };

  const importUrl = useMutation({
    mutationFn: () => playlistsApi.importUrl({ name: playlistForm.name || undefined, url: playlistForm.url }),
    onSuccess: onImported,
    onError: (error) => toast.error(apiErrorMessage(error, 'Import impossible')),
  });

  const importText = useMutation({
    mutationFn: () => playlistsApi.importText({ name: textForm.name || undefined, content: textForm.content }),
    onSuccess: (result) => {
      onImported(result);
      setTextForm({ name: '', content: '' });
    },
    onError: (error) => toast.error(apiErrorMessage(error, 'Import impossible')),
  });

  const importFile = useMutation({
    mutationFn: (file: File) => playlistsApi.importFile(file),
    onSuccess: onImported,
    onError: (error) => toast.error(apiErrorMessage(error, 'Fichier refusé')),
  });

  const importXtream = useMutation({
    mutationFn: () => playlistsApi.importXtream(xtreamForm),
    onSuccess: onImported,
    onError: (error) => toast.error(apiErrorMessage(error, 'Connexion Xtream impossible')),
  });

  const createProvider = useMutation({
    mutationFn: () => providersApi.create({ ...providerForm, kind: providerForm.kind }),
    onSuccess: () => {
      toast.success('Fournisseur ajouté');
      setProviderOpen(false);
      setProviderForm({ name: '', kind: 'm3u', base_url: '', username: '', password: '', notes: '' });
      invalidateAll();
    },
    onError: (error) => toast.error(apiErrorMessage(error, 'Ajout impossible')),
  });

  const testProvider = useMutation({
    mutationFn: (id: string) => providersApi.test(id),
    onSuccess: (result) => (result.ok ? toast.success(result.message) : toast.error(result.message)),
    onError: (error) => toast.error(apiErrorMessage(error, 'Test impossible')),
  });

  const syncPlaylist = useMutation({
    mutationFn: (id: string) => playlistsApi.sync(id),
    onSuccess: onImported,
    onError: (error) => toast.error(apiErrorMessage(error, 'Synchronisation impossible')),
  });

  const deletePlaylist = useMutation({
    mutationFn: (id: string) => playlistsApi.remove(id),
    onSuccess: () => {
      toast.success('Playlist supprimée');
      invalidateAll();
    },
    onError: (error) => toast.error(apiErrorMessage(error, 'Suppression impossible')),
  });

  const deleteProvider = useMutation({
    mutationFn: (id: string) => providersApi.remove(id),
    onSuccess: () => {
      toast.success('Fournisseur supprimé');
      invalidateAll();
    },
    onError: (error) => toast.error(apiErrorMessage(error, 'Suppression impossible')),
  });

  const createEpg = useMutation({
    mutationFn: () => epgApi.create({ name: epgForm.name || undefined, url: epgForm.url }),
    onSuccess: () => {
      toast.success('Source EPG ajoutée');
      setEpgOpen(false);
      setEpgForm({ name: '', url: '' });
      invalidateAll();
    },
    onError: (error) => toast.error(apiErrorMessage(error, 'Ajout impossible')),
  });

  const addFreeEpg = useMutation({
    mutationFn: (source: { name: string; url: string }) => epgApi.create({ name: source.name, url: source.url }),
    onSuccess: () => {
      toast.success('Source EPG libre ajoutée — lancez la synchronisation');
      invalidateAll();
    },
    onError: (error) => toast.error(apiErrorMessage(error, 'Ajout impossible')),
  });

  const syncEpg = useMutation({
    mutationFn: (id: string) => epgApi.sync(id),
    onSuccess: (result) => {
      toast.success(`EPG synchronisé : ${(result as { programmes?: number }).programmes ?? 0} programmes`);
      invalidateAll();
    },
    onError: (error) => toast.error(apiErrorMessage(error, 'Synchronisation EPG impossible')),
  });

  const uploadEpg = useMutation({
    mutationFn: (file: File) => epgApi.upload(file),
    onSuccess: () => {
      toast.success('Fichier XMLTV importé');
      invalidateAll();
    },
    onError: (error) => toast.error(apiErrorMessage(error, 'Fichier XMLTV refusé')),
  });

  const deleteEpg = useMutation({
    mutationFn: (id: string) => epgApi.remove(id),
    onSuccess: () => {
      toast.success('Source EPG supprimée');
      invalidateAll();
    },
    onError: (error) => toast.error(apiErrorMessage(error, 'Suppression impossible')),
  });

  const busy =
    importUrl.isPending || importText.isPending || importFile.isPending || importXtream.isPending || createProvider.isPending;

  return (
    <div className="space-y-5">
      <SectionHeading
        title="Sources & playlists"
        subtitle="Importez vos propres sources autorisées : M3U/M3U8, Xtream, HLS/DASH et EPG XMLTV."
        action={
          <div className="flex flex-wrap gap-2">
            <button type="button" className="btn-soft !py-2" onClick={() => setProviderOpen(true)}>
              <Server className="h-4 w-4" /> Fournisseur
            </button>
            <button type="button" className="btn-soft !py-2" onClick={() => setEpgOpen(true)}>
              <CalendarClock className="h-4 w-4" /> Source EPG
            </button>
            <button type="button" className="btn-primary !py-2" onClick={() => setImportOpen(true)}>
              <Plus className="h-4 w-4" /> Importer
            </button>
          </div>
        }
      />

      <div className="flex flex-wrap gap-2">
        {TABS.map((item) => (
          <button key={item.id} type="button" onClick={() => setTab(item.id)} className={clsx('chip', tab === item.id && 'chip-active')}>
            {item.icon} {item.label}
          </button>
        ))}
      </div>

      {lastResult && <ImportSummary result={lastResult} />}

      {tab === 'playlists' && (
        <div className="surface overflow-hidden">
          <div className="flex items-center justify-between border-b border-white/10 px-4 py-3">
            <h2 className="font-display text-sm font-semibold">Playlists importées</h2>
            <Badge tone="info">{playlists.data?.length ?? 0}</Badge>
          </div>
          {playlists.isLoading ? (
            <LoadingBlock />
          ) : playlists.data?.length ? (
            <ul>
              {playlists.data.map((playlist) => (
                <li key={playlist.id} className="table-row">
                  <div className="min-w-0 flex-1">
                    <p className="truncate font-semibold text-slate-800 dark:text-slate-100">{playlist.name}</p>
                    <p className="truncate text-xs text-slate-500 dark:text-slate-400">
                      {playlist.source_type.toUpperCase()} · {playlist.channel_count} chaînes ·{' '}
                      {playlist.last_sync_at ? `synchronisée ${relativeTime(playlist.last_sync_at)}` : 'jamais synchronisée'}
                    </p>
                    {playlist.last_error && <p className="text-xs text-rose-500">{playlist.last_error}</p>}
                  </div>
                  <Badge tone={playlist.is_active ? 'live' : 'neutral'}>{playlist.is_active ? 'Active' : 'Inactive'}</Badge>
                  <div className="flex gap-1.5">
                    <button
                      type="button"
                      className="btn-soft !px-2.5 !py-1.5 !text-xs"
                      onClick={() => syncPlaylist.mutate(playlist.id)}
                      disabled={syncPlaylist.isPending}
                    >
                      <RefreshCw className={clsx('h-3.5 w-3.5', syncPlaylist.isPending && 'animate-spin')} /> Synchroniser
                    </button>
                    <button
                      type="button"
                      className="btn-ghost !px-2 !py-1.5 text-rose-400"
                      onClick={() => deletePlaylist.mutate(playlist.id)}
                      aria-label={`Supprimer ${playlist.name}`}
                    >
                      <Trash2 className="h-3.5 w-3.5" />
                    </button>
                  </div>
                </li>
              ))}
            </ul>
          ) : (
            <EmptyState
              icon={<FolderDown />}
              title="Aucune playlist"
              description="Importez une URL M3U, un fichier ou un portail Xtream pour démarrer."
              action={
                <button type="button" className="btn-primary" onClick={() => setImportOpen(true)}>
                  Importer une playlist
                </button>
              }
            />
          )}
        </div>
      )}

      {tab === 'playlists' && <FreeSourcesPanel onImported={onImported} />}

      {tab === 'providers' && (
        <div className="surface overflow-hidden">
          <div className="flex items-center justify-between border-b border-white/10 px-4 py-3">
            <h2 className="font-display text-sm font-semibold">Fournisseurs autorisés</h2>
            <Badge tone="info">{providers.data?.length ?? 0}</Badge>
          </div>
          {providers.isLoading ? (
            <LoadingBlock />
          ) : providers.data?.length ? (
            <ul>
              {providers.data.map((provider) => (
                <li key={provider.id} className="table-row">
                  <div className="min-w-0 flex-1">
                    <p className="truncate font-semibold text-slate-800 dark:text-slate-100">{provider.name}</p>
                    <p className="truncate text-xs text-slate-500 dark:text-slate-400">
                      {provider.kind.toUpperCase()} · {provider.channel_count} chaînes · {provider.playlist_count} playlist(s)
                      {provider.base_url ? ` · ${provider.base_url}` : ''}
                    </p>
                  </div>
                  {provider.has_password && <Badge tone="lock">identifiants chiffrés</Badge>}
                  <div className="flex gap-1.5">
                    <button
                      type="button"
                      className="btn-soft !px-2.5 !py-1.5 !text-xs"
                      onClick={() => testProvider.mutate(provider.id)}
                      disabled={testProvider.isPending}
                    >
                      Tester
                    </button>
                    <button
                      type="button"
                      className="btn-ghost !px-2 !py-1.5 text-rose-400"
                      onClick={() => deleteProvider.mutate(provider.id)}
                      aria-label={`Supprimer ${provider.name}`}
                    >
                      <Trash2 className="h-3.5 w-3.5" />
                    </button>
                  </div>
                </li>
              ))}
            </ul>
          ) : (
            <EmptyState icon={<Server />} title="Aucun fournisseur" description="Ajoutez un fournisseur pour regrouper vos playlists et EPG." />
          )}
        </div>
      )}

      {tab === 'epg' && (
        <div className="space-y-4">
          <div className="surface flex flex-wrap items-center justify-between gap-3 p-4">
            <div>
              <h2 className="font-display text-sm font-semibold">Importer un fichier XMLTV</h2>
              <p className="text-xs text-slate-500 dark:text-slate-400">Association automatique par tvg-id, epg_channel_id puis par nom.</p>
            </div>
            <label className="btn-soft cursor-pointer">
              <Upload className="h-4 w-4" /> Choisir un fichier
              <input
                type="file"
                accept=".xml,.xmltv,application/xml,text/xml"
                className="hidden"
                onChange={(event) => {
                  const file = event.target.files?.[0];
                  if (file) uploadEpg.mutate(file);
                  event.target.value = '';
                }}
              />
            </label>
          </div>

          <div className="surface overflow-hidden">
            <div className="border-b border-white/10 px-4 py-3">
              <h2 className="font-display text-sm font-semibold">Guides libres recommandés</h2>
              <p className="text-xs text-slate-500 dark:text-slate-400">
                Association automatique si les <code>tvg-id</code> de vos chaînes correspondent au guide.
              </p>
            </div>
            <ul>
              {FREE_EPG_SOURCES.map((source) => (
                <li key={source.id} className="table-row">
                  <div className="min-w-0 flex-1">
                    <p className="truncate font-semibold text-slate-800 dark:text-slate-100">{source.name}</p>
                    <p className="truncate text-xs text-slate-500 dark:text-slate-400">
                      {source.coverage} · {source.description}
                    </p>
                  </div>
                  <button
                    type="button"
                    className="btn-soft !px-2.5 !py-1.5 !text-xs"
                    onClick={() => addFreeEpg.mutate({ name: source.name, url: source.url })}
                    disabled={addFreeEpg.isPending}
                  >
                    <Plus className="h-3.5 w-3.5" /> Ajouter
                  </button>
                </li>
              ))}
            </ul>
          </div>

          <div className="surface overflow-hidden">
            <div className="flex items-center justify-between border-b border-white/10 px-4 py-3">
              <h2 className="font-display text-sm font-semibold">Sources EPG</h2>
              <Badge tone="info">{epgSources.data?.length ?? 0}</Badge>
            </div>
            {epgSources.isLoading ? (
              <LoadingBlock />
            ) : epgSources.data?.length ? (
              <ul>
                {epgSources.data.map((source) => (
                  <li key={source.id} className="table-row">
                    <div className="min-w-0 flex-1">
                      <p className="truncate font-semibold text-slate-800 dark:text-slate-100">{source.name}</p>
                      <p className="truncate text-xs text-slate-500 dark:text-slate-400">
                        {source.programme_count} programmes · {source.last_sync_at ? `maj ${relativeTime(source.last_sync_at)}` : 'jamais synchronisé'}
                        {source.url ? ` · ${source.url}` : ''}
                      </p>
                      {source.last_error && <p className="text-xs text-rose-500">{source.last_error}</p>}
                    </div>
                    <Badge tone={source.status === 'success' ? 'live' : source.status === 'error' ? 'danger' : 'warning'}>
                      {STATUS_LABELS[source.status] ?? source.status}
                    </Badge>
                    <div className="flex gap-1.5">
                      <button
                        type="button"
                        className="btn-soft !px-2.5 !py-1.5 !text-xs"
                        onClick={() => syncEpg.mutate(source.id)}
                        disabled={!source.url || syncEpg.isPending}
                      >
                        <RefreshCw className={clsx('h-3.5 w-3.5', syncEpg.isPending && 'animate-spin')} /> Synchroniser
                      </button>
                      <button
                        type="button"
                        className="btn-ghost !px-2 !py-1.5 text-rose-400"
                        onClick={() => deleteEpg.mutate(source.id)}
                        aria-label={`Supprimer ${source.name}`}
                      >
                        <Trash2 className="h-3.5 w-3.5" />
                      </button>
                    </div>
                  </li>
                ))}
              </ul>
            ) : (
              <EmptyState icon={<CalendarClock />} title="Aucune source EPG" description="Ajoutez une URL XMLTV ou importez un fichier." />
            )}
          </div>
        </div>
      )}

      {/* Modale d'import */}
      <Modal open={importOpen} onClose={() => setImportOpen(false)} title="Importer une playlist" size="lg">
        <div className="mb-4 flex flex-wrap gap-2">
          {(
            [
              { id: 'url', label: 'URL M3U / HLS', icon: <Link2 className="h-3.5 w-3.5" /> },
              { id: 'file', label: 'Fichier', icon: <FileUp className="h-3.5 w-3.5" /> },
              { id: 'xtream', label: 'Xtream', icon: <Server className="h-3.5 w-3.5" /> },
              { id: 'text', label: 'Coller le contenu', icon: <FolderDown className="h-3.5 w-3.5" /> },
            ] as const
          ).map((item) => (
            <button key={item.id} type="button" className={clsx('chip', mode === item.id && 'chip-active')} onClick={() => setMode(item.id)}>
              {item.icon} {item.label}
            </button>
          ))}
        </div>

        {mode === 'url' && (
          <form
            className="space-y-3"
            onSubmit={(event) => {
              event.preventDefault();
              importUrl.mutate();
            }}
          >
            <div>
              <label className="label" htmlFor="playlist-name">Nom (optionnel)</label>
              <input id="playlist-name" className="input" value={playlistForm.name} onChange={(event) => setPlaylistForm({ ...playlistForm, name: event.target.value })} />
            </div>
            <div>
              <label className="label" htmlFor="playlist-url">URL de la playlist ou du flux</label>
              <input
                id="playlist-url"
                className="input"
                type="url"
                placeholder="https://exemple.com/playlist.m3u8"
                value={playlistForm.url}
                onChange={(event) => setPlaylistForm({ ...playlistForm, url: event.target.value })}
                required
              />
              <p className="mt-1 text-[11px] text-slate-500">M3U, M3U Plus, HLS maître ou fichier .mpd (DASH).</p>
            </div>
            <button type="submit" className="btn-primary w-full" disabled={busy}>
              {importUrl.isPending ? 'Import en cours…' : 'Importer'}
            </button>
          </form>
        )}

        {mode === 'file' && (
          <div className="space-y-3">
            <p className="text-xs text-slate-500 dark:text-slate-400">Formats acceptés : .m3u, .m3u8 (max 40 Mo).</p>
            <input
              ref={fileRef}
              type="file"
              accept=".m3u,.m3u8,audio/x-mpegurl,application/vnd.apple.mpegurl"
              className="input file:mr-3 file:rounded-lg file:border-0 file:bg-brand-500/10 file:px-3 file:py-1.5 file:text-brand-600"
              onChange={(event) => {
                const file = event.target.files?.[0];
                if (file) importFile.mutate(file);
              }}
            />
            {importFile.isPending && <p className="text-xs text-slate-500">Envoi et analyse du fichier…</p>}
          </div>
        )}

        {mode === 'xtream' && (
          <form
            className="space-y-3"
            onSubmit={(event) => {
              event.preventDefault();
              importXtream.mutate();
            }}
          >
            <p className="rounded-xl border border-amber-500/20 bg-amber-500/10 p-3 text-[11px] text-amber-700 dark:text-amber-200">
              Utilisez uniquement vos propres identifiants d’abonnement. Les identifiants sont chiffrés côté serveur.
            </p>
            <div>
              <label className="label" htmlFor="xtream-name">Nom</label>
              <input id="xtream-name" className="input" value={xtreamForm.name} onChange={(event) => setXtreamForm({ ...xtreamForm, name: event.target.value })} placeholder="Mon abonnement" />
            </div>
            <div>
              <label className="label" htmlFor="xtream-url">URL du portail</label>
              <input id="xtream-url" className="input" value={xtreamForm.base_url} onChange={(event) => setXtreamForm({ ...xtreamForm, base_url: event.target.value })} placeholder="http://mon-panneau.tv:8080" required />
            </div>
            <div className="grid gap-3 sm:grid-cols-2">
              <div>
                <label className="label" htmlFor="xtream-user">Identifiant</label>
                <input id="xtream-user" className="input" value={xtreamForm.username} onChange={(event) => setXtreamForm({ ...xtreamForm, username: event.target.value })} required />
              </div>
              <div>
                <label className="label" htmlFor="xtream-pass">Mot de passe</label>
                <input id="xtream-pass" type="password" className="input" value={xtreamForm.password} onChange={(event) => setXtreamForm({ ...xtreamForm, password: event.target.value })} required />
              </div>
            </div>
            <button type="submit" className="btn-primary w-full" disabled={busy}>
              {importXtream.isPending ? 'Connexion…' : 'Connecter et importer'}
            </button>
          </form>
        )}

        {mode === 'text' && (
          <form
            className="space-y-3"
            onSubmit={(event) => {
              event.preventDefault();
              importText.mutate();
            }}
          >
            <div>
              <label className="label" htmlFor="text-name">Nom</label>
              <input id="text-name" className="input" value={textForm.name} onChange={(event) => setTextForm({ ...textForm, name: event.target.value })} />
            </div>
            <div>
              <label className="label" htmlFor="text-content">Contenu M3U</label>
              <textarea
                id="text-content"
                className="input min-h-[160px] font-mono text-xs"
                value={textForm.content}
                onChange={(event) => setTextForm({ ...textForm, content: event.target.value })}
                placeholder={'#EXTM3U\n#EXTINF:-1 tvg-id="..." group-title="Sport",Ma chaîne\nhttps://...'}
                required
              />
            </div>
            <button type="submit" className="btn-primary w-full" disabled={busy}>
              {importText.isPending ? 'Import…' : 'Importer le contenu'}
            </button>
          </form>
        )}
      </Modal>

      {/* Modale fournisseur */}
      <Modal open={providerOpen} onClose={() => setProviderOpen(false)} title="Ajouter un fournisseur">
        <form
          className="space-y-3"
          onSubmit={(event) => {
            event.preventDefault();
            createProvider.mutate();
          }}
        >
          <div>
            <label className="label" htmlFor="provider-name">Nom</label>
            <input id="provider-name" className="input" value={providerForm.name} onChange={(event) => setProviderForm({ ...providerForm, name: event.target.value })} required />
          </div>
          <div>
            <label className="label" htmlFor="provider-kind">Type</label>
            <select id="provider-kind" className="input" value={providerForm.kind} onChange={(event) => setProviderForm({ ...providerForm, kind: event.target.value })}>
              <option value="m3u">Playlist M3U</option>
              <option value="xtream">Portail Xtream Codes</option>
              <option value="hls">Flux HLS</option>
              <option value="dash">Flux DASH</option>
            </select>
          </div>
          <div>
            <label className="label" htmlFor="provider-url">URL de base (optionnel)</label>
            <input id="provider-url" className="input" value={providerForm.base_url} onChange={(event) => setProviderForm({ ...providerForm, base_url: event.target.value })} />
          </div>
          <div className="grid gap-3 sm:grid-cols-2">
            <div>
              <label className="label" htmlFor="provider-user">Identifiant</label>
              <input id="provider-user" className="input" value={providerForm.username} onChange={(event) => setProviderForm({ ...providerForm, username: event.target.value })} />
            </div>
            <div>
              <label className="label" htmlFor="provider-pass">Mot de passe</label>
              <input id="provider-pass" type="password" className="input" value={providerForm.password} onChange={(event) => setProviderForm({ ...providerForm, password: event.target.value })} />
            </div>
          </div>
          <div>
            <label className="label" htmlFor="provider-notes">Notes</label>
            <textarea id="provider-notes" className="input min-h-[70px]" value={providerForm.notes} onChange={(event) => setProviderForm({ ...providerForm, notes: event.target.value })} />
          </div>
          <button type="submit" className="btn-primary w-full" disabled={createProvider.isPending}>
            {createProvider.isPending ? 'Enregistrement…' : 'Ajouter le fournisseur'}
          </button>
        </form>
      </Modal>

      {/* Modale EPG */}
      <Modal open={epgOpen} onClose={() => setEpgOpen(false)} title="Ajouter une source EPG XMLTV">
        <form
          className="space-y-3"
          onSubmit={(event) => {
            event.preventDefault();
            createEpg.mutate();
          }}
        >
          <div>
            <label className="label" htmlFor="epg-name">Nom</label>
            <input id="epg-name" className="input" value={epgForm.name} onChange={(event) => setEpgForm({ ...epgForm, name: event.target.value })} placeholder="EPG France" />
          </div>
          <div>
            <label className="label" htmlFor="epg-url">URL XMLTV</label>
            <input id="epg-url" type="url" className="input" value={epgForm.url} onChange={(event) => setEpgForm({ ...epgForm, url: event.target.value })} placeholder="https://exemple.com/epg.xml" required />
          </div>
          <button type="submit" className="btn-primary w-full" disabled={createEpg.isPending}>
            {createEpg.isPending ? 'Ajout…' : 'Ajouter la source'}
          </button>
          <p className="text-[11px] text-slate-500">
            Vous pouvez aussi importer un fichier XMLTV depuis l’onglet EPG. Association automatique par tvg-id puis par nom.
            Dernière mise à jour : {formatDateTime(new Date().toISOString())}
          </p>
        </form>
      </Modal>
    </div>
  );
}
