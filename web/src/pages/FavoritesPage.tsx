/** Favoris du profil actif avec synchronisation manuelle. */
import { Heart, RefreshCw, Trash2 } from 'lucide-react';
import { useState } from 'react';
import { Link } from 'react-router-dom';
import { favoritesApi } from '@/api/endpoints';
import { useFavorites } from '@/hooks/queries';
import { toast } from '@/store/toast';
import { ChannelCard } from '@/components/ChannelCard';
import { ChannelGridSkeleton } from '@/components/ChannelGrid';
import { EmptyState, SectionHeading } from '@/components/ui';

export function FavoritesPage() {
  const { data: favorites, isLoading, refetch } = useFavorites();
  const [syncing, setSyncing] = useState(false);

  const sync = async () => {
    setSyncing(true);
    try {
      await favoritesApi.sync((favorites ?? []).map((item) => item.channel_id));
      await refetch();
      toast.success('Favoris synchronisés');
    } catch {
      toast.error('Synchronisation impossible');
    } finally {
      setSyncing(false);
    }
  };

  const channels = (favorites ?? []).map((item) => item.channel).filter(Boolean);

  return (
    <div className="space-y-5">
      <SectionHeading
        title="Mes favoris"
        subtitle={`${favorites?.length ?? 0} chaîne(s) enregistrée(s) pour le profil actif`}
        action={
          <div className="flex gap-2">
            <button type="button" className="btn-soft !py-2" onClick={() => void refetch()}>
              <RefreshCw className="h-4 w-4" /> Actualiser
            </button>
            <button type="button" className="btn-ghost !py-2" onClick={() => void sync()} disabled={syncing}>
              <Trash2 className="h-4 w-4" /> {syncing ? 'Synchronisation…' : 'Synchroniser'}
            </button>
          </div>
        }
      />

      {isLoading ? (
        <ChannelGridSkeleton count={6} />
      ) : channels.length ? (
        <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3 2xl:grid-cols-4">
          {channels.map((channel) => (
            <ChannelCard key={channel!.id} channel={{ ...channel!, is_favorite: true }} />
          ))}
        </div>
      ) : (
        <EmptyState
          icon={<Heart />}
          title="Aucun favori pour ce profil"
          description="Cliquez sur le cœur d’une chaîne pour la retrouver ici. Chaque profil possède sa propre liste."
          action={
            <Link to="/channels" className="btn-primary">
              Parcourir les chaînes
            </Link>
          }
        />
      )}
    </div>
  );
}
