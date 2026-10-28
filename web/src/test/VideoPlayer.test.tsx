import { describe, expect, it, vi } from 'vitest';
import { screen } from '@testing-library/react';
import { VideoPlayer } from '@/components/VideoPlayer';
import type { Playback } from '@/api/types';
import { renderWithProviders, sampleChannel } from '@/test/utils';

const playback: Playback = {
  channel_id: 'channel-1',
  url: 'http://localhost:8000/api/v1/streams/proxy?url=x',
  direct_url: 'https://example.com/live.m3u8',
  stream_type: 'hls',
  is_encrypted: false,
  encryption: 'none',
  drm_systems: [],
  variants: [{ label: '720p', bandwidth: 1280000, resolution: '1280x720' }],
  subtitles: ['Français'],
  audio_tracks: [],
  has_keys: false,
  key_system: null,
  clearkey_license: null,
  message: null,
};

describe('VideoPlayer', () => {
  it('bloque les flux DRM sans clé utilisateur', () => {
    renderWithProviders(
      <VideoPlayer
        playback={{ ...playback, is_encrypted: true, encryption: 'widevine', drm_systems: ['widevine'] }}
        channel={sampleChannel}
      />,
    );
    expect(screen.getByText(/ne contourne pas ces protections/i)).toBeInTheDocument();
  });

  it('affiche les contrôles pour un flux HLS libre', () => {
    renderWithProviders(<VideoPlayer playback={playback} channel={sampleChannel} />);
    expect(screen.getByLabelText('Lecture')).toBeInTheDocument();
    expect(screen.getByLabelText('Plein écran')).toBeInTheDocument();
    expect(screen.getByLabelText('Picture in Picture')).toBeInTheDocument();
  });

  it('monte une balise vidéo prête pour le streaming', () => {
    const onProgress = vi.fn();
    const { container } = renderWithProviders(
      <VideoPlayer playback={playback} channel={sampleChannel} onProgress={onProgress} />,
    );
    const video = container.querySelector('video');
    expect(video).not.toBeNull();
    expect(video?.getAttribute('playsinline')).not.toBeNull();
    expect(onProgress).not.toHaveBeenCalled();
  });
});
