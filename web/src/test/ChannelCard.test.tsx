import { describe, expect, it } from 'vitest';
import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ChannelCard } from '@/components/ChannelCard';
import { useUiStore } from '@/store/ui';
import { renderWithProviders, sampleChannel } from '@/test/utils';

describe('ChannelCard', () => {
  it('affiche le nom, la catégorie et la langue', () => {
    renderWithProviders(<ChannelCard channel={sampleChannel} />);
    expect(screen.getByText('beIN SPORTS 1 HD')).toBeInTheDocument();
    expect(screen.getByText(/Sport/)).toBeInTheDocument();
    expect(screen.getByText(/Arabic/)).toBeInTheDocument();
    expect(screen.getByText('HD')).toBeInTheDocument();
  });

  it('ouvre le lecteur au clic', async () => {
    renderWithProviders(<ChannelCard channel={sampleChannel} />);
    await userEvent.click(screen.getByRole('button', { name: /Lire beIN/i }));
    expect(useUiStore.getState().playerChannelId).toBe('channel-1');
    useUiStore.getState().closePlayer();
  });

  it('signale les chaînes chiffrées', () => {
    renderWithProviders(
      <ChannelCard channel={{ ...sampleChannel, is_encrypted: true, encryption: 'widevine', status: 'encrypted' }} />,
    );
    expect(screen.getByText(/Widevine/i)).toBeInTheDocument();
  });

  it('affiche le badge radio', () => {
    renderWithProviders(<ChannelCard channel={{ ...sampleChannel, is_radio: true, stream_type: 'audio' }} />);
    expect(screen.getAllByText('Radio').length).toBeGreaterThan(0);
  });
});
