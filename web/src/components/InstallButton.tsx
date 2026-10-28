/** Bouton « Installer l'application » : invite native de la PWA (masqué si indisponible). */
import { Download } from 'lucide-react';
import { useInstallPrompt } from '@/hooks/useInstallPrompt';

export function InstallButton() {
  const { canInstall, install } = useInstallPrompt();
  if (!canInstall) return null;

  return (
    <button
      type="button"
      onClick={() => void install()}
      className="btn-ghost hidden !px-2.5 !py-2 sm:flex"
      aria-label="Installer PrimeTV sur cet appareil"
      title="Installer PrimeTV sur cet appareil"
    >
      <Download className="h-4 w-4" />
      <span className="hidden text-xs font-semibold xl:inline">Installer</span>
    </button>
  );
}
