/** Primitives d'interface réutilisables (boutons, badges, cartes, modales...). */
import { clsx } from 'clsx';
import { AlertTriangle, CheckCircle2, Info, Loader2, X } from 'lucide-react';
import type { ReactNode } from 'react';
import { useEffect } from 'react';
import { useToastStore } from '@/store/toast';

export function Spinner({ className }: { className?: string }) {
  return <Loader2 className={clsx('h-5 w-5 animate-spin text-brand-400', className)} />;
}

export function LoadingBlock({ label = 'Chargement…' }: { label?: string }) {
  return (
    <div className="flex items-center justify-center gap-3 py-14 text-sm text-slate-500 dark:text-slate-400">
      <Spinner />
      {label}
    </div>
  );
}

export function EmptyState({
  icon,
  title,
  description,
  action,
}: {
  icon?: ReactNode;
  title: string;
  description?: string;
  action?: ReactNode;
}) {
  return (
    <div className="surface flex flex-col items-center justify-center gap-3 px-6 py-14 text-center">
      <div className="rounded-2xl bg-brand-500/10 p-3 text-brand-500 dark:text-brand-300">{icon ?? <Info />}</div>
      <h3 className="font-display text-lg font-semibold">{title}</h3>
      {description && <p className="max-w-md text-sm text-slate-500 dark:text-slate-400">{description}</p>}
      {action}
    </div>
  );
}

export function Badge({
  children,
  tone = 'neutral',
  className,
}: {
  children: ReactNode;
  tone?: 'neutral' | 'live' | 'warning' | 'danger' | 'success' | 'info' | 'lock';
  className?: string;
}) {
  const tones: Record<string, string> = {
    neutral: 'bg-slate-500/15 text-slate-600 dark:text-slate-300',
    live: 'bg-emerald-500/15 text-emerald-600 dark:text-emerald-300',
    warning: 'bg-amber-500/15 text-amber-600 dark:text-amber-300',
    danger: 'bg-rose-500/15 text-rose-600 dark:text-rose-300',
    success: 'bg-emerald-500/15 text-emerald-600 dark:text-emerald-300',
    info: 'bg-brand-500/15 text-brand-600 dark:text-brand-300',
    lock: 'bg-purple-500/15 text-purple-600 dark:text-purple-300',
  };
  return <span className={clsx('badge', tones[tone], className)}>{children}</span>;
}

export function StatCard({
  label,
  value,
  hint,
  icon,
}: {
  label: string;
  value: string | number;
  hint?: string;
  icon?: ReactNode;
}) {
  return (
    <div className="stat-card group">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">{label}</p>
          <p className="mt-2 font-display text-3xl font-bold text-slate-900 dark:text-white">{value}</p>
          {hint && <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">{hint}</p>}
        </div>
        {icon && (
          <div className="rounded-xl bg-gradient-to-br from-brand-500/20 to-accent-500/10 p-2.5 text-brand-600 transition group-hover:scale-105 dark:text-brand-300">
            {icon}
          </div>
        )}
      </div>
      <div className="pointer-events-none absolute inset-x-0 -bottom-10 h-16 bg-gradient-to-t from-brand-500/10 to-transparent" />
    </div>
  );
}

export function SectionHeading({
  title,
  subtitle,
  action,
}: {
  title: string;
  subtitle?: string;
  action?: ReactNode;
}) {
  return (
    <div className="mb-4 flex flex-wrap items-end justify-between gap-3">
      <div>
        <h2 className="font-display text-xl font-bold text-slate-900 dark:text-white">{title}</h2>
        {subtitle && <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">{subtitle}</p>}
      </div>
      {action}
    </div>
  );
}

export function Modal({
  open,
  onClose,
  title,
  children,
  size = 'md',
}: {
  open: boolean;
  onClose: () => void;
  title?: string;
  children: ReactNode;
  size?: 'sm' | 'md' | 'lg' | 'xl';
}) {
  useEffect(() => {
    if (!open) return;
    const onKey = (event: KeyboardEvent) => {
      if (event.key === 'Escape') onClose();
    };
    document.addEventListener('keydown', onKey);
    document.body.style.overflow = 'hidden';
    return () => {
      document.removeEventListener('keydown', onKey);
      document.body.style.overflow = '';
    };
  }, [open, onClose]);

  if (!open) return null;
  const sizes = { sm: 'max-w-md', md: 'max-w-xl', lg: 'max-w-3xl', xl: 'max-w-5xl' };
  return (
    <div className="fixed inset-0 z-[80] flex items-start justify-center overflow-y-auto bg-night-950/80 p-4 backdrop-blur-sm sm:items-center">
      <div
        role="dialog"
        aria-modal="true"
        aria-label={title}
        className={clsx('surface my-auto w-full animate-fade-up p-5 sm:p-6', sizes[size])}
      >
        <div className="mb-4 flex items-start justify-between gap-4">
          {title && <h3 className="font-display text-lg font-bold text-slate-900 dark:text-white">{title}</h3>}
          <button type="button" onClick={onClose} className="btn-ghost !px-2 !py-1.5" aria-label="Fermer">
            <X className="h-4 w-4" />
          </button>
        </div>
        {children}
      </div>
    </div>
  );
}

export function Toaster() {
  const { toasts, dismiss } = useToastStore();
  const icons = {
    success: <CheckCircle2 className="h-4 w-4 text-emerald-400" />,
    error: <AlertTriangle className="h-4 w-4 text-rose-400" />,
    info: <Info className="h-4 w-4 text-brand-400" />,
  };
  return (
    <div className="pointer-events-none fixed bottom-4 right-4 z-[100] flex w-full max-w-sm flex-col gap-2">
      {toasts.map((item) => (
        <div
          key={item.id}
          className="pointer-events-auto flex animate-fade-up items-start gap-3 rounded-xl border border-white/10 bg-night-900/95 px-4 py-3 text-sm text-slate-100 shadow-card backdrop-blur"
        >
          <span className="mt-0.5">{icons[item.kind]}</span>
          <p className="flex-1 leading-snug">{item.message}</p>
          <button type="button" onClick={() => dismiss(item.id)} aria-label="Fermer">
            <X className="h-4 w-4 opacity-60 hover:opacity-100" />
          </button>
        </div>
      ))}
    </div>
  );
}

export function Toggle({
  checked,
  onChange,
  label,
  description,
}: {
  checked: boolean;
  onChange: (value: boolean) => void;
  label: string;
  description?: string;
}) {
  return (
    <label className="flex cursor-pointer items-center justify-between gap-4 py-2">
      <span>
        <span className="block text-sm font-medium text-slate-800 dark:text-slate-100">{label}</span>
        {description && <span className="mt-0.5 block text-xs text-slate-500 dark:text-slate-400">{description}</span>}
      </span>
      <button
        type="button"
        role="switch"
        aria-checked={checked}
        aria-label={label}
        onClick={() => onChange(!checked)}
        className={clsx(
          'relative h-6 w-11 shrink-0 rounded-full transition-colors',
          checked ? 'bg-brand-500' : 'bg-slate-300 dark:bg-white/15',
        )}
      >
        <span
          className={clsx(
            'absolute top-0.5 h-5 w-5 rounded-full bg-white shadow transition-all',
            checked ? 'left-[22px]' : 'left-0.5',
          )}
        />
      </button>
    </label>
  );
}

export function ProgressBar({ value, label }: { value: number; label?: string }) {
  return (
    <div>
      {label && (
        <div className="mb-1 flex justify-between text-xs text-slate-500 dark:text-slate-400">
          <span>{label}</span>
          <span>{Math.round(value)}%</span>
        </div>
      )}
      <div className="h-2 overflow-hidden rounded-full bg-slate-200 dark:bg-white/10">
        <div
          className="h-full rounded-full bg-gradient-to-r from-brand-500 to-accent-400 transition-all duration-500"
          style={{ width: `${Math.min(100, Math.max(0, value))}%` }}
        />
      </div>
    </div>
  );
}
