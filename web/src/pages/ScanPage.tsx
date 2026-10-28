/** Scan & actualisation : lancement, progression temps réel, historique. */
import { clsx } from 'clsx';
import { Activity, AlertTriangle, CheckCircle2, Lock, Radar, RefreshCw, ShieldAlert, Wifi, XCircle } from 'lucide-react';
import { useEffect, useState } from 'react';
import { apiErrorMessage } from '@/api/client';
import { useLatestScan, usePlaylists, useScanJob, useScanJobs, useStartScan } from '@/hooks/queries';
import { formatDateTime, relativeTime, STATUS_LABELS } from '@/lib/format';
import { toast } from '@/store/toast';
import { Badge, EmptyState, ProgressBar, SectionHeading, StatCard, Toggle } from '@/components/ui';

export function ScanPage() {
  const [probe, setProbe] = useState(true);
  const [playlistId, setPlaylistId] = useState('');
  const [jobId, setJobId] = useState<string | null>(null);
  const startScan = useStartScan();
  const { data: playlists } = usePlaylists();
  const { data: jobs, refetch: refetchJobs } = useScanJobs();
  const { data: latest } = useLatestScan();
  const { data: activeJob } = useScanJob(jobId ?? latest?.id ?? null);

  useEffect(() => {
    if (startScan.data?.id) setJobId(startScan.data.id);
  }, [startScan.data?.id]);

  const launch = () => {
    startScan.mutate(
      { probe, playlist_id: playlistId || undefined },
      {
        onSuccess: (job) => {
          setJobId(job.id);
          toast.success('Scan lancé : les flux sont testés en arrière-plan');
        },
        onError: (error) => toast.error(apiErrorMessage(error, 'Impossible de lancer le scan')),
      },
    );
  };

  const job = activeJob ?? (jobId ? undefined : latest ?? undefined);
  const progress = job ? (job.total ? Math.round((job.progress / job.total) * 100) : job.progress) : 0;

  return (
    <div className="space-y-6">
      <SectionHeading
        title="Scan & actualisation"
        subtitle="Teste les flux, détecte le chiffrement (AES-128, ClearKey, DRM) et met à jour le catalogue."
        action={
          <button type="button" className="btn-soft !py-2" onClick={() => void refetchJobs()}>
            <RefreshCw className="h-4 w-4" /> Rafraîchir
          </button>
        }
      />

      <div className="grid gap-4 lg:grid-cols-3">
        <section className="surface space-y-4 p-5 lg:col-span-1">
          <h2 className="font-display text-sm font-semibold text-slate-900 dark:text-white">Nouveau scan</h2>
          <div>
            <label className="label" htmlFor="scan-playlist">Périmètre</label>
            <select id="scan-playlist" className="input" value={playlistId} onChange={(event) => setPlaylistId(event.target.value)}>
              <option value="">Tout le catalogue</option>
              {(playlists ?? []).map((playlist) => (
                <option key={playlist.id} value={playlist.id}>
                  {playlist.name} ({playlist.channel_count})
                </option>
              ))}
            </select>
          </div>
          <Toggle
            checked={probe}
            onChange={setProbe}
            label="Tester réellement les flux"
            description="Requêtes HTTP + analyse du manifeste HLS/DASH (recommandé)"
          />
          <button type="button" className="btn-primary w-full" onClick={launch} disabled={startScan.isPending}>
            <Radar className={clsx('h-4 w-4', startScan.isPending && 'animate-spin')} />
            {startScan.isPending ? 'Lancement…' : 'Lancer le scan'}
          </button>
          <p className="rounded-xl border border-amber-500/20 bg-amber-500/10 p-3 text-[11px] leading-relaxed text-amber-700 dark:text-amber-200">
            <ShieldAlert className="mb-1 h-3.5 w-3.5" /> PrimeTV identifie les chaînes chiffrées et permet de saisir
            <strong> vos propres clés ClearKey</strong>. Aucun contournement de DRM n’est effectué : les flux Widevine,
            PlayReady et FairPlay sont signalés et exclus de la lecture.
          </p>
        </section>

        <section className="surface p-5 lg:col-span-2">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <h2 className="font-display text-sm font-semibold text-slate-900 dark:text-white">Progression</h2>
            {job && (
              <Badge tone={job.status === 'done' ? 'success' : job.status === 'failed' ? 'danger' : 'info'}>
                {STATUS_LABELS[job.status] ?? job.status}
              </Badge>
            )}
          </div>

          {job ? (
            <div className="mt-4 space-y-4">
              <ProgressBar value={progress} label={`${job.progress}/${job.total || '?'} chaînes traitées`} />
              <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
                <div className="rounded-xl border border-white/10 bg-white/5 p-3">
                  <p className="flex items-center gap-1 text-[11px] text-slate-500 dark:text-slate-400"><CheckCircle2 className="h-3 w-3 text-emerald-400" /> Actifs</p>
                  <p className="font-display text-xl font-bold text-emerald-500">{job.active}</p>
                </div>
                <div className="rounded-xl border border-white/10 bg-white/5 p-3">
                  <p className="flex items-center gap-1 text-[11px] text-slate-500 dark:text-slate-400"><XCircle className="h-3 w-3 text-rose-400" /> Hors ligne</p>
                  <p className="font-display text-xl font-bold text-rose-500">{job.offline}</p>
                </div>
                <div className="rounded-xl border border-white/10 bg-white/5 p-3">
                  <p className="flex items-center gap-1 text-[11px] text-slate-500 dark:text-slate-400"><Lock className="h-3 w-3 text-purple-400" /> Chiffrés</p>
                  <p className="font-display text-xl font-bold text-purple-500">{job.encrypted}</p>
                </div>
                <div className="rounded-xl border border-white/10 bg-white/5 p-3">
                  <p className="flex items-center gap-1 text-[11px] text-slate-500 dark:text-slate-400"><AlertTriangle className="h-3 w-3 text-amber-400" /> DRM</p>
                  <p className="font-display text-xl font-bold text-amber-500">{job.drm_protected}</p>
                </div>
              </div>
              <div className="max-h-40 overflow-y-auto rounded-xl border border-white/10 bg-night-950/40 p-3 font-mono text-[11px] text-slate-400">
                {job.logs.length ? job.logs.slice(-12).map((line, index) => <p key={index}>{line}</p>) : <p>Aucun log pour ce job.</p>}
              </div>
              <p className="text-xs text-slate-500">
                Démarré {relativeTime(job.started_at ?? job.created_at)}
                {job.finished_at ? ` · terminé ${relativeTime(job.finished_at)}` : ''}
                {job.error ? ` · erreur : ${job.error}` : ''}
              </p>
            </div>
          ) : (
            <EmptyState icon={<Radar />} title="Aucun scan récent" description="Lancez un scan pour vérifier vos flux et détecter les chaînes chiffrées." />
          )}
        </section>
      </div>

      <div className="grid gap-3 sm:grid-cols-3">
        <StatCard label="Chaînes scannées" value={latest?.total ?? 0} hint={latest ? formatDateTime(latest.finished_at ?? latest.started_at) : undefined} icon={<Activity className="h-5 w-5" />} />
        <StatCard label="Flux actifs" value={latest?.active ?? 0} hint="Dernier scan terminé" icon={<Wifi className="h-5 w-5" />} />
        <StatCard label="Chaînes chiffrées" value={latest?.encrypted ?? 0} hint={`${latest?.drm_protected ?? 0} protégées par DRM`} icon={<Lock className="h-5 w-5" />} />
      </div>

      <div className="surface overflow-hidden">
        <div className="border-b border-white/10 px-4 py-3">
          <h2 className="font-display text-sm font-semibold text-slate-900 dark:text-white">Historique des scans</h2>
        </div>
        {jobs?.length ? (
          <ul>
            {jobs.map((item) => (
              <li key={item.id} className="table-row">
                <div className="min-w-0 flex-1">
                  <p className="text-xs font-semibold text-slate-700 dark:text-slate-200">
                    {formatDateTime(item.started_at ?? item.created_at)} · {item.probe ? 'avec test réseau' : 'sans test'}
                  </p>
                  <p className="text-[11px] text-slate-500">
                    {item.total} chaînes · {item.active} actives · {item.encrypted} chiffrées · {item.drm_protected} DRM
                  </p>
                </div>
                <Badge tone={item.status === 'done' ? 'success' : item.status === 'failed' ? 'danger' : 'info'}>
                  {STATUS_LABELS[item.status] ?? item.status}
                </Badge>
                <button type="button" className="btn-soft !px-2.5 !py-1.5 !text-xs" onClick={() => setJobId(item.id)}>
                  Détails
                </button>
              </li>
            ))}
          </ul>
        ) : (
          <div className="p-4 text-sm text-slate-500">Aucun scan enregistré.</div>
        )}
      </div>
    </div>
  );
}
