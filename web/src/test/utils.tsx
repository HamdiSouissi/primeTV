/** Utilitaires de test : rendu avec providers. */
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render } from '@testing-library/react';
import type { ReactElement } from 'react';
import { MemoryRouter } from 'react-router-dom';
import type { Channel } from '@/api/types';

export function renderWithProviders(ui: ReactElement, { route = '/' }: { route?: string } = {}) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false, gcTime: 0 } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={[route]}>{ui}</MemoryRouter>
    </QueryClientProvider>,
  );
}

export const sampleChannel: Channel = {
  id: 'channel-1',
  name: 'beIN SPORTS 1 HD',
  logo: null,
  stream_type: 'hls',
  group_title: 'Sport | Arabic',
  country: 'QA',
  quality: 'HD',
  is_radio: false,
  is_encrypted: false,
  encryption: 'none',
  drm_systems: [],
  status: 'active',
  priority: 77,
  tvg_id: 'bein1.qa',
  epg_channel_id: 'bein1.qa',
  category: { id: 'cat-1', name: 'Sport', slug: 'sport', icon: 'trophy', color: '#22c55e', position: 0 },
  language: { id: 'lang-1', code: 'ar', name: 'Arabic', native_name: 'العربية', flag: '🇸🇦', position: 0 },
  bouquets: [],
  is_favorite: false,
  last_checked_at: null,
};
