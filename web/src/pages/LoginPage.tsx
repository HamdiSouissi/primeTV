/** Connexion : panneau marketing + formulaire JWT. */
import { Eye, EyeOff, KeyRound, LogIn, ShieldCheck, Sparkles, Tv, Wifi } from 'lucide-react';
import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { apiErrorMessage } from '@/api/client';
import { authApi } from '@/api/endpoints';
import { usePublicConfig } from '@/hooks/queries';
import { APP_NAME, APP_TAGLINE } from '@/lib/constants';
import { useAuthStore } from '@/store/auth';
import { toast } from '@/store/toast';
import { Spinner } from '@/components/ui';

const FEATURES = [
  { icon: Wifi, title: 'HLS · DASH · MPEG-TS', text: 'Lecture adaptative, qualité manuelle et Picture in Picture.' },
  { icon: Sparkles, title: 'Classement automatique', text: 'Catégories, langues et bouquets déduits à l’import.' },
  { icon: ShieldCheck, title: 'Multi-profils & JWT', text: 'Favoris et reprise de lecture isolés par profil.' },
];

export function LoginPage() {
  const navigate = useNavigate();
  const setSession = useAuthStore((state) => state.setSession);
  const { data: config } = usePublicConfig();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);

  const onSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    setLoading(true);
    try {
      const tokens = await authApi.login(email, password);
      setSession(tokens);
      toast.success(`Bienvenue ${tokens.user.username} !`);
      navigate('/', { replace: true });
    } catch (error) {
      toast.error(apiErrorMessage(error, 'Connexion impossible'));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="grid min-h-screen bg-slate-100 dark:bg-night-950 lg:grid-cols-2">
      <section className="relative hidden overflow-hidden bg-night-950 p-12 text-white lg:flex lg:flex-col lg:justify-between">
        <div className="absolute inset-0 bg-mesh-dark" />
        <div className="relative">
          <div className="flex items-center gap-3">
            <span className="flex h-11 w-11 items-center justify-center rounded-xl bg-gradient-to-br from-brand-500 to-accent-500 shadow-glow">
              <Tv className="h-5 w-5" />
            </span>
            <div>
              <p className="font-display text-xl font-extrabold">{APP_NAME}</p>
              <p className="text-xs uppercase tracking-[0.2em] text-slate-400">Open source IPTV</p>
            </div>
          </div>
          <h1 className="mt-14 max-w-lg font-display text-4xl font-extrabold leading-tight text-balance">
            Toute votre télévision, <span className="bg-gradient-to-r from-brand-300 to-accent-300 bg-clip-text text-transparent">sport et chaînes arabes en tête.</span>
          </h1>
          <p className="mt-4 max-w-md text-sm text-slate-300">{APP_TAGLINE} Playlists M3U, Xtream, EPG XMLTV et scan automatique des flux.</p>
        </div>
        <ul className="relative mt-10 space-y-4">
          {FEATURES.map((feature) => (
            <li key={feature.title} className="flex items-start gap-3 rounded-2xl border border-white/10 bg-white/5 p-4 backdrop-blur">
              <span className="rounded-lg bg-brand-500/20 p-2 text-brand-200">
                <feature.icon className="h-4 w-4" />
              </span>
              <div>
                <p className="text-sm font-semibold">{feature.title}</p>
                <p className="text-xs text-slate-400">{feature.text}</p>
              </div>
            </li>
          ))}
        </ul>
        <p className="relative text-xs text-slate-500">
          Plateforme 100 % open source (licences MIT / Apache / BSD) — aucun service propriétaire.
        </p>
      </section>

      <section className="flex items-center justify-center px-5 py-12">
        <div className="w-full max-w-md">
          <div className="mb-8 flex items-center gap-3 lg:hidden">
            <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-brand-500 to-accent-500">
              <Tv className="h-5 w-5 text-white" />
            </span>
            <p className="font-display text-xl font-extrabold">{APP_NAME}</p>
          </div>

          <h2 className="font-display text-2xl font-bold text-slate-900 dark:text-white">Connexion</h2>
          <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">Accédez à votre catalogue et à vos profils.</p>

          <form onSubmit={onSubmit} className="mt-7 space-y-4">
            <div>
              <label className="label" htmlFor="email">
                Email ou nom d’utilisateur
              </label>
              <input
                id="email"
                type="text"
                autoComplete="username"
                className="input"
                value={email}
                onChange={(event) => setEmail(event.target.value)}
                placeholder="admin@primetv.io"
                required
              />
            </div>
            <div>
              <label className="label" htmlFor="password">
                Mot de passe
              </label>
              <div className="relative">
                <input
                  id="password"
                  type={showPassword ? 'text' : 'password'}
                  autoComplete="current-password"
                  className="input pr-11"
                  value={password}
                  onChange={(event) => setPassword(event.target.value)}
                  placeholder="••••••••"
                  required
                />
                <button
                  type="button"
                  onClick={() => setShowPassword((value) => !value)}
                  className="absolute right-2 top-1/2 -translate-y-1/2 rounded-lg p-1.5 text-slate-400 hover:text-slate-600 dark:hover:text-slate-200"
                  aria-label={showPassword ? 'Masquer le mot de passe' : 'Afficher le mot de passe'}
                >
                  {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                </button>
              </div>
            </div>

            <button type="submit" className="btn-primary w-full" disabled={loading}>
              {loading ? <Spinner className="text-white" /> : <LogIn className="h-4 w-4" />}
              {loading ? 'Connexion…' : 'Se connecter'}
            </button>
          </form>

          <div className="mt-5 rounded-xl border border-brand-500/20 bg-brand-500/5 p-3 text-xs text-slate-600 dark:text-slate-300">
            <p className="flex items-center gap-1.5 font-semibold text-brand-700 dark:text-brand-300">
              <KeyRound className="h-3.5 w-3.5" /> Compte administrateur initial
            </p>
            <p className="mt-1 font-mono text-[11px]">admin@primetv.io · PrimeTV#2026</p>
            <p className="mt-1 text-[11px] text-slate-500">
              Modifiez ce mot de passe après la première connexion (Réglages → Compte).
            </p>
          </div>

          {config?.allow_registration && (
            <p className="mt-6 text-center text-sm text-slate-500 dark:text-slate-400">
              Pas encore de compte ?{' '}
              <Link to="/register" className="font-semibold text-brand-600 hover:underline dark:text-brand-300">
                Créer un compte
              </Link>
            </p>
          )}
        </div>
      </section>
    </div>
  );
}
