/** Création de compte (désactivable côté API via ALLOW_REGISTRATION). */
import { ArrowLeft, UserPlus } from 'lucide-react';
import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { apiErrorMessage } from '@/api/client';
import { authApi } from '@/api/endpoints';
import { useAuthStore } from '@/store/auth';
import { toast } from '@/store/toast';
import { Spinner } from '@/components/ui';

export function RegisterPage() {
  const navigate = useNavigate();
  const setSession = useAuthStore((state) => state.setSession);
  const [form, setForm] = useState({ email: '', username: '', full_name: '', password: '', confirm: '' });
  const [loading, setLoading] = useState(false);

  const update = (key: keyof typeof form) => (event: React.ChangeEvent<HTMLInputElement>) =>
    setForm((previous) => ({ ...previous, [key]: event.target.value }));

  const onSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    if (form.password !== form.confirm) {
      toast.error('Les mots de passe ne correspondent pas');
      return;
    }
    setLoading(true);
    try {
      const tokens = await authApi.register({
        email: form.email,
        username: form.username,
        password: form.password,
        full_name: form.full_name || undefined,
      });
      setSession(tokens);
      toast.success('Compte créé, bienvenue !');
      navigate('/', { replace: true });
    } catch (error) {
      toast.error(apiErrorMessage(error, 'Création du compte impossible'));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-slate-100 px-4 py-12 dark:bg-night-950 dark:bg-mesh-dark">
      <div className="surface w-full max-w-md p-6 sm:p-8">
        <Link to="/login" className="inline-flex items-center gap-1.5 text-xs font-semibold text-slate-500 hover:text-brand-500">
          <ArrowLeft className="h-3.5 w-3.5" /> Retour à la connexion
        </Link>
        <h1 className="mt-4 font-display text-2xl font-bold text-slate-900 dark:text-white">Créer un compte</h1>
        <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
          Un profil « Principal » sera créé automatiquement. Vous pourrez en ajouter d’autres.
        </p>

        <form onSubmit={onSubmit} className="mt-6 space-y-4">
          <div>
            <label className="label" htmlFor="full_name">Nom complet</label>
            <input id="full_name" className="input" value={form.full_name} onChange={update('full_name')} placeholder="Amine Ben Salah" />
          </div>
          <div>
            <label className="label" htmlFor="email">Email</label>
            <input id="email" type="email" className="input" value={form.email} onChange={update('email')} required />
          </div>
          <div>
            <label className="label" htmlFor="username">Nom d’utilisateur</label>
            <input id="username" className="input" value={form.username} onChange={update('username')} minLength={3} required />
          </div>
          <div className="grid gap-3 sm:grid-cols-2">
            <div>
              <label className="label" htmlFor="password">Mot de passe</label>
              <input id="password" type="password" className="input" value={form.password} onChange={update('password')} minLength={8} required />
            </div>
            <div>
              <label className="label" htmlFor="confirm">Confirmation</label>
              <input id="confirm" type="password" className="input" value={form.confirm} onChange={update('confirm')} minLength={8} required />
            </div>
          </div>
          <p className="text-[11px] text-slate-500 dark:text-slate-400">
            8 caractères minimum, lettres et chiffres. Ne réutilisez pas un mot de passe existant.
          </p>
          <button type="submit" className="btn-primary w-full" disabled={loading}>
            {loading ? <Spinner className="text-white" /> : <UserPlus className="h-4 w-4" />}
            {loading ? 'Création…' : 'Créer mon compte'}
          </button>
        </form>
      </div>
    </div>
  );
}
