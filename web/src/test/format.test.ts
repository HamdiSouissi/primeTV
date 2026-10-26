import { describe, expect, it } from 'vitest';
import { channelInitials, clamp, formatDuration, formatNumber, formatTime, relativeTime } from '@/lib/format';

describe('format', () => {
  it('formate les nombres en français', () => {
    expect(formatNumber(12345)).toMatch(/12\s?345/);
  });

  it('formate les durées', () => {
    expect(formatDuration(45)).toBe('45s');
    expect(formatDuration(125)).toBe('2m 05s');
    expect(formatDuration(3700)).toBe('1h 01m');
    expect(formatDuration(0)).toBe('—');
  });

  it('gère les dates invalides', () => {
    expect(formatTime(undefined)).toBe('—');
    expect(relativeTime(null)).toBe('jamais');
  });

  it('calcule des initiales', () => {
    expect(channelInitials('beIN SPORTS 1')).toBe('BS');
    expect(channelInitials('قناة')).toBe('ق');
  });

  it('borne les valeurs', () => {
    expect(clamp(5, 0, 3)).toBe(3);
    expect(clamp(-1, 0, 3)).toBe(0);
  });
});
