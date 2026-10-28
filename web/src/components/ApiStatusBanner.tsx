/**
 * Bannière globale « API injoignable ».
 *
 * Affichée au-dessus de toute l'application (y compris l'écran de connexion)
 * dès qu'une requête reçoit un 502/503/504 ou échoue faute de réponse.
 * Elle donne la cause probable, la commande de diagnostic et un bouton de
 * nouvelle tentative — au lieu d'un échec de connexion silencieux.
 */
import { AlertTriangle, RefreshCw, Server, WifiOff } from 'lucide-react';
import { useState } from 'react';
import { useApiStatusStore } from '@/store/apiStatus';

const HINTS: Record<string, { title: string; text: string; command: string }> = {
  unreachable: {
    title: 'L’API PrimeTV ne répond pas (502)',
    text: 'Le proxy Nginx fonctionne mais le conteneur « backend » est arrêté, en cours de démarrage ou en erreur. L’interface réessaiera automatiquement à la prochaine action.',
    command: 'docker compose ps\ndocker compose logs --tail=80 backend',
  },
  offline: {
    title: 'Serveur injoignable',
    text: 'Aucune réponse du serveur : connexion réseau coupée, mauvaise URL, ou pile Docker arrêtée.',
    command: 'docker compose up -d\ndocker compose logs --tail=50 nginx backend',
  },
};

export function ApiStatusBanner() {
  const { status, detail, since } = useApiStatusStore();
  const [checking, setChecking] = useState(false);

  if (status === 'ok') return null;
  const hint = HINTS[status] ?? HINTS.offline;

  const retry = async () => {
    setChecking(true);
    try {
      // Sonde directe, sans passer par le client (qui mettrait à jour l'état).
      const response = await fetch('/healthz', { cache: 'no-store' });
      if (response.ok) {
        window.location.reload();
        return;
      }
    } catch {
      /* toujours injoignable : on laisse la bannière visible */
    } finally {
      setChecking(false);
    }
  };

  return (
    <div
      role="alert"
      className="relative z-50 border-b border-rose-500/40 bg-rose-500/10 px-4 py-3 text-rose-900 backdrop-blur dark:text-rose-100"
    >
      <div className="mx-auto flex w-full max-w-[1500px] flex-col gap-2 sm:flex-row sm:items-start">
        <span className="mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-rose-500/15">
          {status === 'offline' ? <WifiOff className="h-4 w-4" /> : <Server className="h-4 w-4" />}
        </span>
        <div className="min-w-0 flex-1">
          <p className="flex items-center gap-2 text-sm font-semibold">
            <AlertTriangle className="h-4 w-4" />
            {hint.title}
          </p>
          <p className="mt-0.5 text-xs leading-relaxed text-rose-800/90 dark:text-rose-200/90">{hint.text}</p>
          <pre className="mt-1.5 overflow-x-auto rounded-lg bg-rose-950/20 px-2 py-1.5 text-[11px] leading-relaxed text-rose-900 dark:bg-black/30 dark:text-rose-200">
            {hint.command}
          </pre>
          {detail && (
            <p className="mt-1 text-[11px] text-rose-700/80 dark:text-rose-300/70">
              Détail : {detail}
              {since ? ` · depuis ${new Date(since).toLocaleTimeString('fr-FR')}` : ''}
            </p>
          )}
        </div>
        <button
          type="button"
          onClick={() => void retry()}
          disabled={checking}
          className="btn-soft shrink-0 !border-rose-400/40 !bg-rose-500/10 !px-3 !py-1.5 !text-xs !text-rose-900 hover:!bg-rose-500/20 dark:!text-rose-100"
        >
          <RefreshCw className={`h-3.5 w-3.5 ${checking ? 'animate-spin' : ''}`} />
          {checking ? 'Vérification…' : 'Réessayer'}
        </button>
      </div>
    </div>
  );
}
