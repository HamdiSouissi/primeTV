/** Fenêtre de lecture plein écran (playback + EPG + favoris + clés). */
import { clsx } from 'clsx';
import { Heart, KeyRound, Lock, Radio, RefreshCw, Tv, X } from 'lucide-react';
import { useEffect, useState } from 'react';
import { apiErrorMessage } from '@/api/client';
import { channelsApi } from '@/api/endpoints';
import type { Playback } from '@/api/types';
import { useChannel, useChannelEpg, usePlayback, useRecordHistory, useRefreshChannel, useToggleFavorite } from '@/hooks/queries';
import { ENCRYPTION_LABELS, formatTime } from '@/lib/format';
import { useAuthStore } from '@/store/auth';
import { toast } from '@/store/toast';
import { useUiStore } from '@/store/ui';
import { VideoPlayer } from '@/components/VideoPlayer';
import { Badge, LoadingBlock } from '@/components/ui';

function KeysForm({ playback, onSaved }: { playback: Playback; onSaved: () => void }) {
  const [kid, setKid] = useState('');
  const [key, setKey] = useState('');
  const [saving, setSaving] = useState(false);

  const submit = async (event: React.FormEvent) => {
    event.preventDefault();
    setSaving(true);
    try {
      await channelsApi.setKey(playback.channel_id, kid, key);
      toast.success('Clé enregistrée pour ce flux');
      setKid('');
      setKey('');
      onSaved();
    } catch (error) {
      toast.error(apiErrorMessage(error, 'Clé refusée'));
    } finally {
      setSaving(false);
    }
  };

  return (
    <form onSubmit={submit} className="mt-3 space-y-3 rounded-xl border border-white/10 bg-white/5 p-3">
      <p className="text-xs text-slate-400">
        Enregistrez une clé <strong>ClearKey / AES-128</strong> que vous êtes en droit d’utiliser (contenu libre ou
        abonnement). PrimeTV ne fournit ni ne devine aucune clé.
      </p>
      <div className="grid gap-2 sm:grid-cols-2">
        <div>
          <label className="label" htmlFor="kid">
            Key ID (KID)
          </label>
          <input id="kid" className="input font-mono text-xs" value={kid} onChange={(event) => setKid(event.target.value)} placeholder="32 caractères hex" required />
        </div>
        <div>
          <label className="label" htmlFor="key">
            Clé
          </label>
          <input id="key" className="input font-mono text-xs" value={key} onChange={(event) => setKey(event.target.value)} placeholder="32 caractères hex" required />
        </div>
      </div>
      <button type="submit" className="btn-primary w-full" disabled={saving}>
        <KeyRound className="h-4 w-4" /> {saving ? 'Enregistrement…' : 'Enregistrer la clé'}
      </button>
    </form>
  );
}

export function PlayerOverlay() {
  const channelId = useUiStore((state) => state.playerChannelId);
  const closePlayer = useUiStore((state) => state.closePlayer);
  const profileId = useAuthStore((state) => state.profileId);
  const { data: channel, isLoading: channelLoading, refetch: refetchChannel } = useChannel(channelId);
  const { data: playback, isLoading: playLoading, error, refetch } = usePlayback(channelId);
  const { data: epg } = useChannelEpg(channelId);
  const recordHistory = useRecordHistory();
  const toggleFavorite = useToggleFavorite();
  const refreshChannel = useRefreshChannel();
  const [showKeys, setShowKeys] = useState(false);
  const [continueAt, setContinueAt] = useState(0);

  useEffect(() => {
    setContinueAt(0);
    setShowKeys(false);
  }, [channelId]);

  useEffect(() => {
    if (!channelId) return;
    const onKey = (event: KeyboardEvent) => {
      if (event.key === 'Escape') closePlayer();
    };
    document.addEventListener('keydown', onKey);
    document.body.style.overflow = 'hidden';
    return () => {
      document.removeEventListener('keydown', onKey);
      document.body.style.overflow = '';
    };
  }, [channelId, closePlayer]);

  if (!channelId) return null;

  const reportProgress = (position: number, duration: number) => {
    recordHistory.mutate({
      channel_id: channelId,
      position_seconds: position,
      duration_seconds: duration || undefined,
      device: 'web',
    });
  };

  return (
    <div className="fixed inset-0 z-[70] overflow-y-auto bg-night-950/95 backdrop-blur">
      <div className="mx-auto flex min-h-full w-full max-w-6xl flex-col gap-4 p-3 sm:p-6">
        <div className="flex items-center justify-between gap-3">
          <div className="flex min-w-0 items-center gap-3">
            <div className="flex h-11 w-16 shrink-0 items-center justify-center overflow-hidden rounded-xl bg-night-800 ring-1 ring-white/10">
              {channel?.logo ? (
                <img src={channel.logo} alt="" className="h-full w-full object-contain p-1" />
              ) : (
                <Tv className="h-5 w-5 text-slate-400" />
              )}
            </div>
            <div className="min-w-0">
              <h2 className="truncate font-display text-lg font-bold text-white sm:text-xl" dir="auto">
                {channel?.name ?? 'Chargement…'}
              </h2>
              <div className="mt-1 flex flex-wrap items-center gap-1.5">
                {channel?.category && <Badge tone="info">{channel.category.name}</Badge>}
                {channel?.language && (
                  <Badge tone="neutral">
                    {channel.language.flag} {channel.language.name}
                  </Badge>
                )}
                {channel?.quality && <Badge tone="success">{channel.quality}</Badge>}
                {channel?.is_radio && (
                  <Badge tone="info">
                    <Radio className="h-3 w-3" /> Radio
                  </Badge>
                )}
                {channel?.is_encrypted && (
                  <Badge tone="lock">
                    <Lock className="h-3 w-3" /> {ENCRYPTION_LABELS[channel.encryption] ?? channel.encryption}
                  </Badge>
                )}
              </div>
            </div>
          </div>
          <button type="button" onClick={closePlayer} className="btn-ghost !px-2.5 !py-2" aria-label="Fermer le lecteur">
            <X className="h-5 w-5" />
          </button>
        </div>

        {playLoading || channelLoading ? (
          <div className="surface flex aspect-video items-center justify-center">
            <LoadingBlock label="Préparation du flux…" />
          </div>
        ) : error || !playback || !channel ? (
          <div className="surface flex aspect-video flex-col items-center justify-center gap-3 text-center">
            <p className="text-sm text-slate-300">
              {apiErrorMessage(error, 'Impossible de préparer la lecture de cette chaîne.')}
            </p>
            <button type="button" className="btn-ghost" onClick={() => void refetch()}>
              <RefreshCw className="h-4 w-4" /> Réessayer
            </button>
          </div>
        ) : (
          <VideoPlayer
            playback={playback}
            channel={channel}
            startPosition={continueAt}
            onProgress={reportProgress}
            onClose={closePlayer}
          />
        )}

        <div className="grid gap-3 lg:grid-cols-3">
          <div className="surface p-4 lg:col-span-2">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <h3 className="font-display text-sm font-semibold text-white">Programme</h3>
              <div className="flex flex-wrap gap-2">
                <button
                  type="button"
                  className="btn-soft !px-3 !py-1.5 !text-xs"
                  onClick={() => {
                    if (channel) {
                      toggleFavorite.mutate({ channelId: channel.id, isFavorite: channel.is_favorite });
                    }
                  }}
                >
                  <Heart className={clsx('h-3.5 w-3.5', channel?.is_favorite && 'fill-rose-500 text-rose-500')} />
                  {channel?.is_favorite ? 'Dans les favoris' : 'Ajouter aux favoris'}
                </button>
                <button
                  type="button"
                  className="btn-soft !px-3 !py-1.5 !text-xs"
                  onClick={() => refreshChannel.mutate(channelId, { onSuccess: () => void refetchChannel() })}
                  disabled={refreshChannel.isPending}
                >
                  <RefreshCw className={clsx('h-3.5 w-3.5', refreshChannel.isPending && 'animate-spin')} /> Tester le flux
                </button>
                {playback?.is_encrypted && !playback.drm_systems.length && (
                  <button type="button" className="btn-soft !px-3 !py-1.5 !text-xs" onClick={() => setShowKeys((value) => !value)}>
                    <KeyRound className="h-3.5 w-3.5" /> Ajouter mes clés
                  </button>
                )}
              </div>
            </div>

            {epg?.current ? (
              <div className="mt-3 space-y-1.5">
                <p className="text-sm font-semibold text-white" dir="auto">
                  {epg.current.title}
                </p>
                <p className="text-xs text-slate-400">
                  {formatTime(epg.current.start_at)} – {formatTime(epg.current.stop_at)}
                  {epg.current.category ? ` · ${epg.current.category}` : ''}
                </p>
                {typeof epg.current.progress === 'number' && (
                  <div className="h-1.5 overflow-hidden rounded-full bg-white/10">
                    <div
                      className="h-full rounded-full bg-gradient-to-r from-brand-500 to-accent-400"
                      style={{ width: `${epg.current.progress * 100}%` }}
                    />
                  </div>
                )}
                {epg.current.description && <p className="line-clamp-3 text-xs text-slate-400">{epg.current.description}</p>}
                {epg.next && (
                  <p className="pt-1 text-xs text-slate-500">
                    À suivre : <span className="text-slate-300">{epg.next.title}</span> à {formatTime(epg.next.start_at)}
                  </p>
                )}
              </div>
            ) : (
              <p className="mt-3 text-xs text-slate-500">
                Aucun programme EPG associé. Importez un fichier XMLTV dans le guide TV pour enrichir cette chaîne.
              </p>
            )}

            {playback?.message && (
              <p className="mt-3 rounded-xl border border-amber-500/20 bg-amber-500/10 p-3 text-xs text-amber-200">
                {playback.message}
              </p>
            )}
            {showKeys && playback && (
              <div className="mt-3">
                <KeysForm playback={playback} onSaved={() => void refetch()} />
              </div>
            )}
          </div>

          <div className="surface p-4">
            <h3 className="font-display text-sm font-semibold text-white">Informations du flux</h3>
            <dl className="mt-3 space-y-2 text-xs text-slate-400">
              <div className="flex justify-between gap-3">
                <dt>Type</dt>
                <dd className="font-semibold uppercase text-slate-200">{playback?.stream_type ?? '—'}</dd>
              </div>
              <div className="flex justify-between gap-3">
                <dt>Chiffrement</dt>
                <dd className="font-semibold text-slate-200">
                  {playback?.is_encrypted ? ENCRYPTION_LABELS[playback.encryption] ?? playback.encryption : 'Aucun'}
                </dd>
              </div>
              <div className="flex justify-between gap-3">
                <dt>Variantes</dt>
                <dd className="font-semibold text-slate-200">{playback?.variants.length ?? 0}</dd>
              </div>
              <div className="flex justify-between gap-3">
                <dt>Sous-titres</dt>
                <dd className="font-semibold text-slate-200">{playback?.subtitles.length ?? 0}</dd>
              </div>
              <div className="flex justify-between gap-3">
                <dt>Statut</dt>
                <dd className="font-semibold text-slate-200">{channel?.status ?? '—'}</dd>
              </div>
            </dl>
            <p className="mt-4 text-[11px] leading-relaxed text-slate-500">
              Rappel : ne diffusez que des flux que vous êtes autorisé à regarder. Les DRM ne sont pas contournés.
            </p>
            {profileId && <p className="mt-2 text-[11px] text-slate-600">Session profil #{profileId.slice(0, 8)}</p>}
          </div>
        </div>
      </div>
    </div>
  );
}
