import { describe, expect, it, vi } from 'vitest';
import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { FreeSourcesPanel } from '@/components/FreeSourcesPanel';
import { FREE_EPG_SOURCES, FREE_SOURCES, FREE_SOURCE_GROUPS, sourcesByGroup } from '@/lib/freeSources';
import { renderWithProviders } from '@/test/utils';
import { playlistsApi } from '@/api/endpoints';

describe('catalogue de sources libres', () => {
  it('ne contient que des URLs HTTPS uniques', () => {
    const urls = FREE_SOURCES.map((source) => source.url);
    expect(new Set(urls).size).toBe(urls.length);
    for (const url of urls) expect(url.startsWith('https://')).toBe(true);
    for (const epg of FREE_EPG_SOURCES) expect(epg.url.startsWith('https://')).toBe(true);
  });

  it('couvre toutes les catégories de présentation', () => {
    for (const group of FREE_SOURCE_GROUPS) {
      expect(sourcesByGroup(group).length).toBeGreaterThan(0);
    }
    expect(sourcesByGroup().length).toBe(FREE_SOURCES.length);
  });

  it('ne référence aucun nom de source illégale connue', () => {
    const forbidden = ['iptv-premium', 'panel', 'activation', 'crack', 'xtream-codes-premium'];
    const haystack = JSON.stringify(FREE_SOURCES).toLowerCase();
    for (const word of forbidden) expect(haystack.includes(word)).toBe(false);
  });

  it('décrit chaque source (nom, description, estimation)', () => {
    for (const source of FREE_SOURCES) {
      expect(source.name.length).toBeGreaterThan(2);
      expect(source.description.length).toBeGreaterThan(10);
      expect(source.channels.length).toBeGreaterThan(0);
      expect(['communauté', 'diffuseur']).toContain(source.kind);
    }
  });
});

describe('FreeSourcesPanel', () => {
  it('affiche les sources du groupe par défaut', () => {
    renderWithProviders(<FreeSourcesPanel onImported={vi.fn()} />);
    expect(screen.getByText('Sources libres prêtes à l’emploi')).toBeInTheDocument();
    expect(screen.getByText('Actualités internationales')).toBeInTheDocument();
  });

  it('filtre par groupe', async () => {
    renderWithProviders(<FreeSourcesPanel onImported={vi.fn()} />);
    await userEvent.click(screen.getByRole('button', { name: 'Sport' }));
    expect(screen.getByText('Sport', { selector: 'p' })).toBeInTheDocument();
    expect(screen.queryByText('Actualités internationales')).not.toBeInTheDocument();
  });

  it('importe la source sélectionnée et remonte le résultat', async () => {
    const result = {
      playlist: {
        id: 'pl-1',
        name: 'Actualités internationales (libre)',
        source_type: 'url' as const,
        url: FREE_SOURCES[0].url,
        file_name: null,
        provider_id: null,
        channel_count: 3,
        is_active: true,
        auto_sync: false,
        last_sync_at: null,
        last_error: null,
        created_at: '2026-10-26T00:00:00Z',
        updated_at: '2026-10-26T00:00:00Z',
      },
      total: 3,
      created: 2,
      updated: 1,
      skipped: 0,
      radios: 0,
      encrypted: 0,
      categories: { news: 3 },
      warnings: [],
      epg_urls: [],
      epg_sources: [],
    };
    const spy = vi.spyOn(playlistsApi, 'importUrl').mockResolvedValue(result);
    const onImported = vi.fn();

    renderWithProviders(<FreeSourcesPanel onImported={onImported} />);
    await userEvent.click(screen.getByRole('button', { name: /Importer Actualités internationales/ }));

    await waitFor(() => expect(spy).toHaveBeenCalledWith({
      name: 'Actualités internationales (libre)',
      url: FREE_SOURCES[0].url,
    }));
    expect(onImported).toHaveBeenCalledWith(result);
    spy.mockRestore();
  });
});
