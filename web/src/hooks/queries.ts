/** Hooks TanStack Query : lectures et mutations de l'API PrimeTV. */
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { catalogApi, channelsApi, epgApi, favoritesApi, historyApi, playlistsApi, profilesApi, providersApi, scanApi, settingsApi, statsApi } from '@/api/endpoints';
import type { ChannelQuery } from '@/api/types';

export const queryKeys = {
  dashboard: ['dashboard'] as const,
  facets: ['facets'] as const,
  quickFilters: ['quick-filters'] as const,
  config: ['config'] as const,
  channels: (query: ChannelQuery) => ['channels', query] as const,
  channel: (id: string | null) => ['channel', id] as const,
  playback: (id: string | null, proxy: boolean) => ['playback', id, proxy] as const,
  favorites: ['favorites'] as const,
  history: ['history'] as const,
  continueWatching: ['history', 'continue'] as const,
  playlists: ['playlists'] as const,
  providers: ['providers'] as const,
  epgSources: ['epg-sources'] as const,
  guide: (hours: number) => ['guide', hours] as const,
  jobs: ['scan-jobs'] as const,
  latestJob: ['scan-job-latest'] as const,
  profiles: ['profiles'] as const,
  settings: ['settings'] as const,
  activity: ['activity'] as const,
};

export function usePublicConfig() {
  return useQuery({ queryKey: queryKeys.config, queryFn: catalogApi.config, staleTime: 300_000 });
}

export function useDashboard() {
  return useQuery({ queryKey: queryKeys.dashboard, queryFn: statsApi.dashboard });
}

export function useFacets() {
  return useQuery({ queryKey: queryKeys.facets, queryFn: catalogApi.facets, staleTime: 60_000 });
}

export function useQuickFilters() {
  return useQuery({ queryKey: queryKeys.quickFilters, queryFn: catalogApi.quickFilters, staleTime: 60_000 });
}

export function useChannels(query: ChannelQuery) {
  return useQuery({
    queryKey: queryKeys.channels(query),
    queryFn: () => channelsApi.list(query),
    placeholderData: (previous) => previous,
  });
}

export function useChannel(id: string | null) {
  return useQuery({
    queryKey: queryKeys.channel(id),
    queryFn: () => channelsApi.get(id as string),
    enabled: Boolean(id),
  });
}

export function usePlayback(id: string | null, proxy = true) {
  return useQuery({
    queryKey: queryKeys.playback(id, proxy),
    queryFn: () => channelsApi.play(id as string, proxy),
    enabled: Boolean(id),
    staleTime: 20_000,
    retry: 1,
  });
}

export function useChannelEpg(id: string | null) {
  return useQuery({
    queryKey: ['channel-epg', id] as const,
    queryFn: () => channelsApi.epg(id as string),
    enabled: Boolean(id),
    staleTime: 60_000,
  });
}

export function useFavorites() {
  return useQuery({ queryKey: queryKeys.favorites, queryFn: favoritesApi.list });
}

export function useToggleFavorite() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ channelId, isFavorite }: { channelId: string; isFavorite: boolean }) =>
      isFavorite ? favoritesApi.remove(channelId) : favoritesApi.add(channelId),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.favorites });
      void queryClient.invalidateQueries({ queryKey: ['channels'] });
      void queryClient.invalidateQueries({ queryKey: queryKeys.dashboard });
    },
  });
}

export function useContinueWatching() {
  return useQuery({ queryKey: queryKeys.continueWatching, queryFn: () => historyApi.continueWatching(12) });
}

export function useHistory(limit = 50) {
  return useQuery({ queryKey: [...queryKeys.history, limit], queryFn: () => historyApi.list(limit) });
}

export function useRecordHistory() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: historyApi.record,
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.history });
      void queryClient.invalidateQueries({ queryKey: queryKeys.continueWatching });
    },
  });
}

export function usePlaylists() {
  return useQuery({ queryKey: queryKeys.playlists, queryFn: playlistsApi.list });
}

export function useProviders() {
  return useQuery({ queryKey: queryKeys.providers, queryFn: providersApi.list });
}

export function useEpgSources() {
  return useQuery({ queryKey: queryKeys.epgSources, queryFn: epgApi.list });
}

export function useGuide(hours = 24) {
  return useQuery({ queryKey: queryKeys.guide(hours), queryFn: () => epgApi.guide({ hours }) });
}

export function useScanJobs() {
  return useQuery({ queryKey: queryKeys.jobs, queryFn: () => scanApi.jobs(15) });
}

export function useLatestScan() {
  return useQuery({ queryKey: queryKeys.latestJob, queryFn: scanApi.latest });
}

export function useScanJob(id: string | null) {
  return useQuery({
    queryKey: ['scan-job', id] as const,
    queryFn: () => scanApi.job(id as string),
    enabled: Boolean(id),
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      return status === 'running' || status === 'queued' ? 1500 : false;
    },
  });
}

export function useStartScan() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: scanApi.start,
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.jobs });
      void queryClient.invalidateQueries({ queryKey: queryKeys.latestJob });
      void queryClient.invalidateQueries({ queryKey: queryKeys.dashboard });
    },
  });
}

export function useProfiles() {
  return useQuery({ queryKey: queryKeys.profiles, queryFn: profilesApi.list });
}

export function useSaveSettings() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ key, value }: { key: string; value: Record<string, unknown> }) =>
      settingsApi.save(key, value),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: queryKeys.settings }),
  });
}

export function useRefreshChannel() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: channelsApi.refresh,
    onSuccess: (_, channelId) => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.channel(channelId) });
      void queryClient.invalidateQueries({ queryKey: ['channels'] });
    },
  });
}
