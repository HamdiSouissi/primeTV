import { describe, expect, it, beforeEach, vi } from 'vitest';
import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ApiStatusBanner } from '@/components/ApiStatusBanner';
import { useApiStatusStore } from '@/store/apiStatus';
import { renderWithProviders } from '@/test/utils';

const realFetch = global.fetch;

beforeEach(() => {
  useApiStatusStore.getState().reset();
  global.fetch = realFetch;
});

describe('ApiStatusBanner', () => {
  it('reste invisible quand l’API répond', () => {
    renderWithProviders(<ApiStatusBanner />);
    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
  });

  it('explique un 502 (backend arrêté) avec les commandes de diagnostic', () => {
    useApiStatusStore.getState().setStatus('unreachable', 'HTTP 502 sur /config');
    renderWithProviders(<ApiStatusBanner />);

    expect(screen.getByRole('alert')).toBeInTheDocument();
    expect(screen.getByText(/L’API PrimeTV ne répond pas \(502\)/)).toBeInTheDocument();
    expect(screen.getByText(/docker compose logs --tail=80 backend/)).toBeInTheDocument();
    expect(screen.getByText(/HTTP 502 sur \/config/)).toBeInTheDocument();
  });

  it('signale une absence totale de réponse (réseau / pile arrêtée)', () => {
    useApiStatusStore.getState().setStatus('offline', 'Network Error');
    renderWithProviders(<ApiStatusBanner />);
    expect(screen.getByText(/Serveur injoignable/)).toBeInTheDocument();
    expect(screen.getByText(/docker compose up -d/)).toBeInTheDocument();
  });

  it('recharge la page quand la sonde /healthz répond', async () => {
    useApiStatusStore.getState().setStatus('unreachable', 'HTTP 502 sur /config');
    const fetchMock = vi.fn().mockResolvedValue({ ok: true });
    global.fetch = fetchMock as unknown as typeof fetch;
    const reload = vi.fn();
    Object.defineProperty(window, 'location', {
      configurable: true,
      value: { ...window.location, reload, pathname: '/', assign: vi.fn() },
    });

    renderWithProviders(<ApiStatusBanner />);
    await userEvent.click(screen.getByRole('button', { name: /Réessayer/ }));

    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith('/healthz', { cache: 'no-store' }));
    await waitFor(() => expect(reload).toHaveBeenCalled());
  });

  it('conserve la bannière si la sonde échoue encore', async () => {
    useApiStatusStore.getState().setStatus('unreachable', 'HTTP 502 sur /config');
    global.fetch = vi.fn().mockRejectedValue(new Error('Network Error')) as unknown as typeof fetch;

    renderWithProviders(<ApiStatusBanner />);
    await userEvent.click(screen.getByRole('button', { name: /Réessayer/ }));
    await waitFor(() => expect(screen.getByRole('alert')).toBeInTheDocument());
  });
});
