/** Grille responsive de chaînes avec états de chargement et vide. */
import { Tv } from 'lucide-react';
import type { Channel } from '@/api/types';
import { ChannelCard } from '@/components/ChannelCard';
import { EmptyState } from '@/components/ui';

export function ChannelGridSkeleton({ count = 8 }: { count?: number }) {
  return (
    <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3 2xl:grid-cols-4">
      {Array.from({ length: count }).map((_, index) => (
        <div key={index} className="surface flex items-center gap-3 p-3">
          <div className="skeleton h-14 w-20 shrink-0" />
          <div className="flex-1 space-y-2">
            <div className="skeleton h-3.5 w-3/4" />
            <div className="skeleton h-3 w-1/2" />
            <div className="skeleton h-4 w-2/3" />
          </div>
        </div>
      ))}
    </div>
  );
}

export function ChannelGrid({
  channels,
  isLoading,
  emptyTitle = 'Aucune chaîne trouvée',
  emptyDescription = 'Modifiez les filtres ou importez une nouvelle playlist.',
  action,
}: {
  channels: Channel[];
  isLoading?: boolean;
  emptyTitle?: string;
  emptyDescription?: string;
  action?: React.ReactNode;
}) {
  if (isLoading) return <ChannelGridSkeleton />;
  if (!channels.length) {
    return <EmptyState icon={<Tv />} title={emptyTitle} description={emptyDescription} action={action} />;
  }
  return (
    <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3 2xl:grid-cols-4">
      {channels.map((channel) => (
        <ChannelCard key={channel.id} channel={channel} />
      ))}
    </div>
  );
}
