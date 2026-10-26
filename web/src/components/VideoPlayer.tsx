/**
 * Lecteur vidéo multi-format : HLS (hls.js), DASH (dash.js), MP4/MPEG-TS (natif).
 * Fonctions : qualité manuelle/auto, sous-titres, PiP, plein écran, reprise, raccourcis clavier.
 */
import Hls, { type Level } from 'hls.js';
import { clsx } from 'clsx';
import {
  AlertTriangle,
  Captions,
  Gauge,
  Loader2,
  Maximize,
  Minimize,
  Pause,
  PictureInPicture2,
  Play,
  RotateCcw,
  Volume2,
  VolumeX,
} from 'lucide-react';
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import type { Channel, Playback } from '@/api/types';

type PlayerStatus = 'loading' | 'ready' | 'error';

export interface VideoPlayerProps {
  playback: Playback;
  channel: Channel;
  startPosition?: number;
  onProgress?: (positionSeconds: number, durationSeconds: number) => void;
  onClose?: () => void;
}

const PROGRESS_INTERVAL_MS = 20_000;

export function VideoPlayer({ playback, channel, startPosition = 0, onProgress }: VideoPlayerProps) {
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const hlsRef = useRef<Hls | null>(null);
  const dashRef = useRef<{ reset: () => void } | null>(null);
  const lastReportRef = useRef(0);

  const [status, setStatus] = useState<PlayerStatus>('loading');
  const [error, setError] = useState<string | null>(null);
  const [playing, setPlaying] = useState(false);
  const [muted, setMuted] = useState(false);
  const [volume, setVolume] = useState(1);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const [levels, setLevels] = useState<{ index: number; label: string }[]>([]);
  const [activeLevel, setActiveLevel] = useState(-1);
  const [subtitleTracks, setSubtitleTracks] = useState<{ index: number; label: string }[]>([]);
  const [activeSubtitle, setActiveSubtitle] = useState(-1);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [attempt, setAttempt] = useState(0);

  const isLive = duration === 0 || !Number.isFinite(duration);
  const isDrm = playback.drm_systems.some((system) => ['widevine', 'playready', 'fairplay'].includes(system));
  const blocked = isDrm && !playback.has_keys;

  const formatTime = useCallback((seconds: number) => {
    if (!Number.isFinite(seconds) || seconds < 0) return '00:00';
    const total = Math.floor(seconds);
    const h = Math.floor(total / 3600);
    const m = Math.floor((total % 3600) / 60);
    const s = total % 60;
    const mm = String(m).padStart(2, '0');
    const ss = String(s).padStart(2, '0');
    return h ? `${h}:${mm}:${ss}` : `${mm}:${ss}`;
  }, []);

  // Initialisation du moteur de lecture
  useEffect(() => {
    const video = videoRef.current;
    if (!video || blocked) return;
    setStatus('loading');
    setError(null);
    setLevels([]);
    setSubtitleTracks([]);
    setActiveLevel(-1);
    setActiveSubtitle(-1);

    const cleanup = () => {
      hlsRef.current?.destroy();
      hlsRef.current = null;
      dashRef.current?.reset();
      dashRef.current = null;
    };
    cleanup();

    const applyStart = () => {
      if (startPosition > 0) {
        try {
          video.currentTime = startPosition;
        } catch {
          /* flux live : ignoré */
        }
      }
    };

    if (playback.stream_type === 'hls') {
      if (Hls.isSupported()) {
        const hls = new Hls({
          enableWorker: true,
          lowLatencyMode: true,
          backBufferLength: 30,
          maxBufferLength: 20,
          manifestLoadingRetryDelay: 800,
          manifestLoadingMaxRetry: 3,
          fragLoadingMaxRetry: 4,
          xhrSetup: (xhr) => {
            xhr.withCredentials = false;
          },
        });
        hlsRef.current = hls;
        hls.loadSource(playback.url);
        hls.attachMedia(video);
        hls.on(Hls.Events.MANIFEST_PARSED, () => {
          setStatus('ready');
          setLevels(
            hls.levels.map((level: Level, index: number) => ({
              index,
              label: level.height ? `${level.height}p` : `${Math.round((level.bitrate || 0) / 1000)} kbps`,
            })),
          );
          setSubtitleTracks(
            hls.subtitleTracks.map((track, index) => ({
              index,
              label: track.name || track.lang || `Sous-titres ${index + 1}`,
            })),
          );
          applyStart();
        });
        hls.on(Hls.Events.LEVEL_SWITCHED, (_event, data) => setActiveLevel(data.level));
        hls.on(Hls.Events.ERROR, (_event, data) => {
          if (data.fatal) {
            setError(
              data.type === Hls.ErrorTypes.NETWORK_ERROR
                ? 'Flux inaccessible. Vérifiez que la source est toujours en ligne.'
                : 'Ce flux ne peut pas être décodé par le navigateur (format ou protection).',
            );
            setStatus('error');
          }
        });
      } else if (video.canPlayType('application/vnd.apple.mpegurl')) {
        video.src = playback.url;
        setStatus('ready');
        applyStart();
      } else {
        setError('HLS non pris en charge par ce navigateur.');
        setStatus('error');
      }
    } else if (playback.stream_type === 'dash') {
      let cancelled = false;
      void import('dashjs').then((module) => {
        if (cancelled) return;
        const player = module.MediaPlayer().create();
        dashRef.current = player;
        player.initialize(video, playback.url, true);
        player.on('streamInitialized', () => {
          setStatus('ready');
          applyStart();
        });
        player.on('error', () => {
          setError('Flux DASH illisible (protection DRM ou source indisponible).');
          setStatus('error');
        });
      });
      return () => {
        cancelled = true;
        cleanup();
      };
    } else {
      video.src = playback.url;
      applyStart();
    }

    return cleanup;
  }, [playback.url, playback.stream_type, blocked, startPosition, attempt]);

  // Suivi de l'état du média
  useEffect(() => {
    const video = videoRef.current;
    if (!video) return;
    const onLoaded = () => {
      setStatus((previous) => (previous === 'error' ? previous : 'ready'));
      setDuration(video.duration || 0);
    };
    const onTime = () => {
      setCurrentTime(video.currentTime);
      setDuration(video.duration || 0);
      if (onProgress && video.currentTime > 0) {
        const now = Date.now();
        if (now - lastReportRef.current > PROGRESS_INTERVAL_MS) {
          lastReportRef.current = now;
          onProgress(Math.floor(video.currentTime), Math.floor(video.duration || 0));
        }
      }
    };
    const onPlay = () => setPlaying(true);
    const onPause = () => setPlaying(false);
    const onWaiting = () => setStatus((previous) => (previous === 'error' ? previous : 'loading'));
    const onPlaying = () => setStatus('ready');
    const onVolume = () => {
      setMuted(video.muted);
      setVolume(video.volume);
    };
    const onError = () => {
      setError('Lecture impossible : la source a refusé la connexion ou le format est protégé.');
      setStatus('error');
    };

    video.addEventListener('loadedmetadata', onLoaded);
    video.addEventListener('timeupdate', onTime);
    video.addEventListener('play', onPlay);
    video.addEventListener('pause', onPause);
    video.addEventListener('waiting', onWaiting);
    video.addEventListener('playing', onPlaying);
    video.addEventListener('volumechange', onVolume);
    video.addEventListener('error', onError);
    return () => {
      video.removeEventListener('loadedmetadata', onLoaded);
      video.removeEventListener('timeupdate', onTime);
      video.removeEventListener('play', onPlay);
      video.removeEventListener('pause', onPause);
      video.removeEventListener('waiting', onWaiting);
      video.removeEventListener('playing', onPlaying);
      video.removeEventListener('volumechange', onVolume);
      video.removeEventListener('error', onError);
    };
  }, [onProgress]);

  // Plein écran
  useEffect(() => {
    const onFullscreenChange = () => setIsFullscreen(Boolean(document.fullscreenElement));
    document.addEventListener('fullscreenchange', onFullscreenChange);
    return () => document.removeEventListener('fullscreenchange', onFullscreenChange);
  }, []);

  const togglePlay = useCallback(() => {
    const video = videoRef.current;
    if (!video) return;
    if (video.paused) void video.play().catch(() => setStatus('error'));
    else video.pause();
  }, []);

  const toggleMute = useCallback(() => {
    const video = videoRef.current;
    if (!video) return;
    video.muted = !video.muted;
  }, []);

  const toggleFullscreen = useCallback(async () => {
    const container = videoRef.current?.parentElement;
    if (!container) return;
    try {
      if (document.fullscreenElement) await document.exitFullscreen();
      else await container.requestFullscreen();
    } catch {
      /* refusé par le navigateur */
    }
  }, []);

  const togglePip = useCallback(async () => {
    const video = videoRef.current;
    if (!video || !document.pictureInPictureEnabled) return;
    try {
      if (document.pictureInPictureElement) await document.exitPictureInPicture();
      else await video.requestPictureInPicture();
    } catch {
      /* ignoré */
    }
  }, []);

  const selectLevel = (index: number) => {
    if (!hlsRef.current) return;
    hlsRef.current.currentLevel = index;
    setActiveLevel(index);
  };

  const selectSubtitle = (index: number) => {
    if (!hlsRef.current) return;
    hlsRef.current.subtitleTrack = index;
    setActiveSubtitle(index);
  };

  // Raccourcis clavier
  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if (['INPUT', 'TEXTAREA', 'SELECT'].includes((event.target as HTMLElement)?.tagName)) return;
      switch (event.key.toLowerCase()) {
        case ' ':
        case 'k':
          event.preventDefault();
          togglePlay();
          break;
        case 'm':
          toggleMute();
          break;
        case 'f':
          void toggleFullscreen();
          break;
        case 'p':
          void togglePip();
          break;
        default:
          break;
      }
    };
    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  }, [togglePlay, toggleMute, toggleFullscreen, togglePip]);

  const qualityOptions = useMemo(
    () => [{ index: -1, label: 'Auto' }, ...levels],
    [levels],
  );

  if (blocked) {
    return (
      <div className="flex aspect-video w-full flex-col items-center justify-center gap-3 rounded-2xl border border-amber-500/30 bg-night-900/90 p-6 text-center">
        <AlertTriangle className="h-8 w-8 text-amber-400" />
        <p className="max-w-lg text-sm text-slate-200">
          {playback.message ??
            'Ce flux est protégé par un système DRM (Widevine/PlayReady/FairPlay). PrimeTV ne contourne pas ces protections.'}
        </p>
        <p className="max-w-lg text-xs text-slate-400">
          Ajoutez une source libre dans « Sources & playlists » ou utilisez votre propre lecteur agréé.
        </p>
      </div>
    );
  }

  return (
    <div className="group relative w-full overflow-hidden rounded-2xl bg-black shadow-card">
      <div className="relative aspect-video w-full">
        <video
          ref={videoRef}
          className="h-full w-full bg-black"
          playsInline
          autoPlay
          controls={false}
          crossOrigin="anonymous"
          poster={channel.logo ?? undefined}
        />

        {status === 'loading' && (
          <div className="absolute inset-0 flex flex-col items-center justify-center gap-3 bg-night-950/70">
            <Loader2 className="h-8 w-8 animate-spin text-brand-400" />
            <p className="text-xs text-slate-300">
              Connexion au flux {playback.stream_type.toUpperCase()}
              {playback.has_keys ? ' — déchiffrement avec vos clés' : ''}…
            </p>
          </div>
        )}

        {status === 'error' && (
          <div className="absolute inset-0 flex flex-col items-center justify-center gap-3 bg-night-950/85 p-6 text-center">
            <AlertTriangle className="h-8 w-8 text-rose-400" />
            <p className="max-w-md text-sm text-slate-200">{error}</p>
            <div className="flex flex-wrap justify-center gap-2">
              <button type="button" className="btn-ghost" onClick={() => setAttempt((value) => value + 1)}>
                <RotateCcw className="h-4 w-4" /> Réessayer
              </button>
              <a className="btn-soft" href={playback.direct_url ?? playback.url} target="_blank" rel="noreferrer">
                Ouvrir la source
              </a>
            </div>
          </div>
        )}

        {/* Barre de contrôle */}
        <div className="absolute inset-x-0 bottom-0 bg-gradient-to-t from-black/90 via-black/45 to-transparent px-3 pb-2.5 pt-8 opacity-100 transition-opacity duration-200 sm:opacity-0 sm:group-hover:opacity-100 sm:group-focus-within:opacity-100">
          {!isLive && (
            <input
              type="range"
              min={0}
              max={Math.max(duration, 0)}
              step={1}
              value={currentTime}
              onChange={(event) => {
                const video = videoRef.current;
                if (!video) return;
                video.currentTime = Number(event.target.value);
                setCurrentTime(Number(event.target.value));
              }}
              aria-label="Position de lecture"
              className="mb-2 h-1 w-full cursor-pointer appearance-none rounded-full bg-white/25 accent-brand-500"
            />
          )}
          <div className="flex items-center gap-2 text-white">
            <button type="button" onClick={togglePlay} aria-label={playing ? 'Pause' : 'Lecture'} className="rounded-lg p-1.5 hover:bg-white/15">
              {playing ? <Pause className="h-5 w-5" /> : <Play className="h-5 w-5 fill-current" />}
            </button>
            <button type="button" onClick={toggleMute} aria-label={muted ? 'Activer le son' : 'Couper le son'} className="rounded-lg p-1.5 hover:bg-white/15">
              {muted || volume === 0 ? <VolumeX className="h-5 w-5" /> : <Volume2 className="h-5 w-5" />}
            </button>
            <input
              type="range"
              min={0}
              max={1}
              step={0.05}
              value={muted ? 0 : volume}
              onChange={(event) => {
                const video = videoRef.current;
                if (!video) return;
                video.volume = Number(event.target.value);
                video.muted = Number(event.target.value) === 0;
              }}
              aria-label="Volume"
              className="hidden h-1 w-20 cursor-pointer appearance-none rounded-full bg-white/25 accent-brand-400 sm:block"
            />
            <span className="ml-1 text-[11px] font-medium tabular-nums text-slate-200">
              {isLive ? 'LIVE' : `${formatTime(currentTime)} / ${formatTime(duration)}`}
            </span>

            <div className="ml-auto flex items-center gap-1">
              {qualityOptions.length > 1 && (
                <label className="flex items-center gap-1 rounded-lg bg-white/10 px-2 py-1 text-[11px]">
                  <Gauge className="h-3.5 w-3.5" />
                  <select
                    aria-label="Qualité"
                    className="bg-transparent text-[11px] text-white outline-none [&>option]:text-slate-900"
                    value={activeLevel}
                    onChange={(event) => selectLevel(Number(event.target.value))}
                  >
                    {qualityOptions.map((option) => (
                      <option key={option.index} value={option.index}>
                        {option.label}
                      </option>
                    ))}
                  </select>
                </label>
              )}
              {subtitleTracks.length > 0 && (
                <label className="flex items-center gap-1 rounded-lg bg-white/10 px-2 py-1 text-[11px]">
                  <Captions className="h-3.5 w-3.5" />
                  <select
                    aria-label="Sous-titres"
                    className="bg-transparent text-[11px] text-white outline-none [&>option]:text-slate-900"
                    value={activeSubtitle}
                    onChange={(event) => selectSubtitle(Number(event.target.value))}
                  >
                    <option value={-1}>Off</option>
                    {subtitleTracks.map((track) => (
                      <option key={track.index} value={track.index}>
                        {track.label}
                      </option>
                    ))}
                  </select>
                </label>
              )}
              <button type="button" onClick={togglePip} aria-label="Picture in Picture" className="rounded-lg p-1.5 hover:bg-white/15">
                <PictureInPicture2 className="h-4 w-4" />
              </button>
              <button
                type="button"
                onClick={toggleFullscreen}
                aria-label={isFullscreen ? 'Quitter le plein écran' : 'Plein écran'}
                className="rounded-lg p-1.5 hover:bg-white/15"
              >
                {isFullscreen ? <Minimize className="h-4 w-4" /> : <Maximize className="h-4 w-4" />}
              </button>
            </div>
          </div>
        </div>

        {playback.is_encrypted && (
          <span
            className={clsx(
              'absolute left-3 top-3 rounded-full px-2.5 py-1 text-[11px] font-semibold backdrop-blur',
              playback.has_keys ? 'bg-emerald-500/20 text-emerald-200' : 'bg-purple-500/20 text-purple-200',
            )}
          >
            {playback.has_keys ? 'Clés utilisateur actives' : `Flux chiffré · ${playback.encryption}`}
          </span>
        )}
      </div>
    </div>
  );
}
