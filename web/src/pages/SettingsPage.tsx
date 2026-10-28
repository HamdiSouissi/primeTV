/** Réglages : compte, sécurité, profils, apparence et informations. */
import { clsx } from 'clsx';
import { Check, KeyRound, LogOut, Plus, ShieldCheck, Trash2, UserRound, Users } from 'lucide-react';
import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { apiErrorMessage } from '@/api/client';
import { authApi, profilesApi } from '@/api/endpoints';
import type { Profile } from '@/api/types';
import { useProfiles, usePublicConfig } from '@/hooks/queries';
import { formatDateTime } from '@/lib/format';
import { useAuthStore } from '@/store/auth';
import { toast } from '@/store/toast';
import { useUiStore } from '@/store/ui';
import { useQueryClient } from '@tanstack/react-query';
import { Badge, Modal, SectionHeading, Toggle } from '@/components/ui';

export function SettingsPage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { user, setUser, logout, profileId, setProfileId } = useAuthStore();
  const { theme, setTheme } = useUiStore();
  const { data: profiles } = useProfiles();
  const { data: config } = usePublicConfig();

  const [account, setAccount] = useState({
    full_name: user?.full_name ?? '',
    email: user?.email ?? '',
    username: user?.username ?? '',
  });
  const [passwords, setPasswords] = useState({ current: '', next: '', confirm: '' });
  const [profileModal, setProfileModal] = useState(false);
  const [newProfile, setNewProfile] = useState({ name: '', is_kids: false, pin: '' });
  const [editing, setEditing] = useState<Profile | null>(null);

  const saveAccount = async (event: React.FormEvent) => {
    event.preventDefault();
    try {
      const updated = await authApi.updateMe(account);
      setUser(updated);
      toast.success('Compte mis à jour');
    } catch (error) {
      toast.error(apiErrorMessage(error, 'Mise à jour impossible'));
    }
  };

  const changePassword = async (event: React.FormEvent) => {
    event.preventDefault();
    if (passwords.next !== passwords.confirm) {
      toast.error('Les nouveaux mots de passe ne correspondent pas');
      return;
    }
    try {
      await authApi.changePassword(passwords.current, passwords.next);
      setPasswords({ current: '', next: '', confirm: '' });
      toast.success('Mot de passe modifié');
    } catch (error) {
      toast.error(apiErrorMessage(error, 'Mot de passe refusé'));
    }
  };

  const createProfile = async (event: React.FormEvent) => {
    event.preventDefault();
    try {
      await profilesApi.create({
        name: newProfile.name,
        is_kids: newProfile.is_kids,
        pin: newProfile.pin || undefined,
      });
      await queryClient.invalidateQueries({ queryKey: ['profiles'] });
      setProfileModal(false);
      setNewProfile({ name: '', is_kids: false, pin: '' });
      toast.success('Profil créé');
    } catch (error) {
      toast.error(apiErrorMessage(error, 'Création impossible'));
    }
  };

  const saveProfile = async (profile: Profile, patch: Record<string, unknown>) => {
    try {
      await profilesApi.update(profile.id, patch);
      await queryClient.invalidateQueries({ queryKey: ['profiles'] });
      setEditing(null);
      toast.success('Profil mis à jour');
    } catch (error) {
      toast.error(apiErrorMessage(error, 'Mise à jour impossible'));
    }
  };

  const removeProfile = async (profile: Profile) => {
    if (!window.confirm(`Supprimer le profil « ${profile.name} » ? Favoris et historique associés seront perdus.`)) return;
    try {
      await profilesApi.remove(profile.id);
      await queryClient.invalidateQueries({ queryKey: ['profiles'] });
      if (profileId === profile.id) setProfileId('');
      toast.success('Profil supprimé');
    } catch (error) {
      toast.error(apiErrorMessage(error, 'Suppression impossible'));
    }
  };

  return (
    <div className="space-y-6">
      <SectionHeading title="Réglages" subtitle="Compte, sécurité, profils et apparence." />

      <div className="grid gap-4 lg:grid-cols-2">
        <section className="surface p-5">
          <h2 className="flex items-center gap-2 font-display text-sm font-semibold text-slate-900 dark:text-white">
            <UserRound className="h-4 w-4" /> Compte
          </h2>
          <form className="mt-4 space-y-3" onSubmit={saveAccount}>
            <div>
              <label className="label" htmlFor="account-name">Nom complet</label>
              <input id="account-name" className="input" value={account.full_name} onChange={(event) => setAccount({ ...account, full_name: event.target.value })} />
            </div>
            <div className="grid gap-3 sm:grid-cols-2">
              <div>
                <label className="label" htmlFor="account-email">Email</label>
                <input id="account-email" type="email" className="input" value={account.email} onChange={(event) => setAccount({ ...account, email: event.target.value })} />
              </div>
              <div>
                <label className="label" htmlFor="account-username">Nom d’utilisateur</label>
                <input id="account-username" className="input" value={account.username} onChange={(event) => setAccount({ ...account, username: event.target.value })} />
              </div>
            </div>
            <button type="submit" className="btn-primary !py-2">
              <Check className="h-4 w-4" /> Enregistrer
            </button>
          </form>
          <div className="mt-4 flex flex-wrap gap-2 text-[11px] text-slate-500">
            <Badge tone="info">{user?.role === 'admin' ? 'Administrateur' : 'Utilisateur'}</Badge>
            <Badge tone="neutral">Créé le {formatDateTime(user?.created_at)}</Badge>
          </div>
        </section>

        <section className="surface p-5">
          <h2 className="flex items-center gap-2 font-display text-sm font-semibold text-slate-900 dark:text-white">
            <ShieldCheck className="h-4 w-4" /> Sécurité
          </h2>
          <form className="mt-4 space-y-3" onSubmit={changePassword}>
            <div>
              <label className="label" htmlFor="current-password">Mot de passe actuel</label>
              <input id="current-password" type="password" className="input" value={passwords.current} onChange={(event) => setPasswords({ ...passwords, current: event.target.value })} required />
            </div>
            <div className="grid gap-3 sm:grid-cols-2">
              <div>
                <label className="label" htmlFor="next-password">Nouveau</label>
                <input id="next-password" type="password" className="input" value={passwords.next} onChange={(event) => setPasswords({ ...passwords, next: event.target.value })} minLength={8} required />
              </div>
              <div>
                <label className="label" htmlFor="confirm-password">Confirmation</label>
                <input id="confirm-password" type="password" className="input" value={passwords.confirm} onChange={(event) => setPasswords({ ...passwords, confirm: event.target.value })} minLength={8} required />
              </div>
            </div>
            <button type="submit" className="btn-primary !py-2">
              <KeyRound className="h-4 w-4" /> Modifier le mot de passe
            </button>
          </form>
          <p className="mt-3 text-[11px] text-slate-500">
            Jetons JWT signés HS256, hachage PBKDF2-SHA256, rate limiting et validation systématique des entrées.
          </p>
        </section>

        <section className="surface p-5">
          <div className="flex items-center justify-between">
            <h2 className="flex items-center gap-2 font-display text-sm font-semibold text-slate-900 dark:text-white">
              <Users className="h-4 w-4" /> Profils
            </h2>
            <button type="button" className="btn-soft !px-3 !py-1.5 !text-xs" onClick={() => setProfileModal(true)}>
              <Plus className="h-3.5 w-3.5" /> Ajouter
            </button>
          </div>
          <ul className="mt-3 space-y-2">
            {(profiles ?? []).map((profile) => (
              <li key={profile.id} className="flex flex-wrap items-center gap-2 rounded-xl border border-white/10 bg-white/5 p-3">
                <div className="min-w-0 flex-1">
                  <p className="flex items-center gap-2 text-sm font-semibold text-slate-800 dark:text-slate-100">
                    {profile.name}
                    {profile.is_default && <Badge tone="info">par défaut</Badge>}
                    {profile.is_kids && <Badge tone="warning">kids</Badge>}
                    {profile.has_pin && <Badge tone="lock">PIN</Badge>}
                  </p>
                  <p className="text-[11px] text-slate-500">Langue : {profile.language.toUpperCase()}</p>
                </div>
                <div className="flex gap-1.5">
                  <button type="button" className="btn-ghost !px-2.5 !py-1.5 !text-xs" onClick={() => setProfileId(profile.id)}>
                    Activer
                  </button>
                  <button type="button" className="btn-ghost !px-2 !py-1.5 text-rose-400" onClick={() => void removeProfile(profile)} aria-label={`Supprimer ${profile.name}`}>
                    <Trash2 className="h-3.5 w-3.5" />
                  </button>
                </div>
                {editing?.id === profile.id ? (
                  <form
                    className="flex w-full flex-wrap items-center gap-2"
                    onSubmit={(event) => {
                      event.preventDefault();
                      void saveProfile(profile, { is_kids: editing.is_kids, language: editing.language });
                    }}
                  >
                    <select className="input !w-auto !py-1 !text-xs" value={editing.language} onChange={(event) => setEditing({ ...editing, language: event.target.value })}>
                      {(config?.languages ?? []).map((language) => (
                        <option key={language.code} value={language.code}>
                          {language.name}
                        </option>
                      ))}
                    </select>
                    <label className="flex items-center gap-1 text-xs">
                      <input type="checkbox" checked={editing.is_kids} onChange={(event) => setEditing({ ...editing, is_kids: event.target.checked })} /> Kids
                    </label>
                    <button type="submit" className="btn-soft !px-2.5 !py-1 !text-xs">Enregistrer</button>
                  </form>
                ) : (
                  <button type="button" className="text-[11px] font-semibold text-brand-500 hover:underline" onClick={() => setEditing(profile)}>
                    Modifier
                  </button>
                )}
              </li>
            ))}
          </ul>
        </section>

        <section className="surface p-5">
          <h2 className="font-display text-sm font-semibold text-slate-900 dark:text-white">Apparence</h2>
          <div className="mt-3 space-y-2">
            <Toggle checked={theme === 'dark'} onChange={(value) => setTheme(value ? 'dark' : 'light')} label="Mode sombre" description="Interface sombre (par défaut) ou claire" />
            <div className="rounded-xl border border-white/10 bg-white/5 p-3 text-xs text-slate-500 dark:text-slate-400">
              <p className="font-semibold text-slate-700 dark:text-slate-200">Version</p>
              <p className="mt-1">PrimeTV {config?.version ?? '1.0.0'} · environnement {config?.environment ?? 'development'}</p>
              <p className="mt-1">API REST documentée : <a className="text-brand-500 hover:underline" href="/docs" target="_blank" rel="noreferrer">/docs</a> (Swagger UI)</p>
            </div>
            <button type="button" className={clsx('btn-ghost w-full !py-2 text-rose-400')} onClick={() => { logout(); navigate('/login'); }}>
              <LogOut className="h-4 w-4" /> Se déconnecter
            </button>
          </div>
        </section>
      </div>

      <Modal open={profileModal} onClose={() => setProfileModal(false)} title="Nouveau profil">
        <form className="space-y-3" onSubmit={createProfile}>
          <div>
            <label className="label" htmlFor="profile-name">Nom du profil</label>
            <input id="profile-name" className="input" value={newProfile.name} onChange={(event) => setNewProfile({ ...newProfile, name: event.target.value })} required />
          </div>
          <div>
            <label className="label" htmlFor="profile-pin">Code PIN (optionnel, 4 à 8 chiffres)</label>
            <input id="profile-pin" className="input" value={newProfile.pin} onChange={(event) => setNewProfile({ ...newProfile, pin: event.target.value })} minLength={4} maxLength={8} />
          </div>
          <Toggle checked={newProfile.is_kids} onChange={(value) => setNewProfile({ ...newProfile, is_kids: value })} label="Profil enfant" description="Masque les catégories adultes (filtrage côté interface)" />
          <button type="submit" className="btn-primary w-full">Créer le profil</button>
        </form>
      </Modal>
    </div>
  );
}
