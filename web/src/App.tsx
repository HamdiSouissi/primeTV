/** Routage de l'application et garde d'authentification. */
import { useEffect } from 'react';
import { Navigate, Route, Routes } from 'react-router-dom';
import { Layout } from '@/components/Layout';
import { useProfiles } from '@/hooks/queries';
import { useAuthStore } from '@/store/auth';
import { ChannelsPage } from '@/pages/ChannelsPage';
import { DashboardPage } from '@/pages/DashboardPage';
import { FavoritesPage } from '@/pages/FavoritesPage';
import { GuidePage } from '@/pages/GuidePage';
import { LoginPage } from '@/pages/LoginPage';
import { RegisterPage } from '@/pages/RegisterPage';
import { ScanPage } from '@/pages/ScanPage';
import { SettingsPage } from '@/pages/SettingsPage';
import { SourcesPage } from '@/pages/SourcesPage';
import { Toaster } from '@/components/ui';
import { ApiStatusBanner } from '@/components/ApiStatusBanner';

function ProtectedLayout() {
  const isAuthenticated = useAuthStore((state) => Boolean(state.accessToken));
  const setProfiles = useAuthStore((state) => state.setProfiles);
  const profileId = useAuthStore((state) => state.profileId);
  const { data: profiles } = useProfiles();

  useEffect(() => {
    if (profiles?.length) setProfiles(profiles);
  }, [profiles, setProfiles]);

  if (!isAuthenticated) return <Navigate to="/login" replace />;
  if (!profileId && profiles?.length) {
    return <Navigate to="/" replace />;
  }
  return <Layout />;
}

function GuestOnly({ children }: { children: React.ReactNode }) {
  const isAuthenticated = useAuthStore((state) => Boolean(state.accessToken));
  if (isAuthenticated) return <Navigate to="/" replace />;
  return <>{children}</>;
}

export function App() {
  return (
    <>
      <ApiStatusBanner />
      <Routes>
        <Route
          path="/login"
          element={
            <GuestOnly>
              <LoginPage />
            </GuestOnly>
          }
        />
        <Route
          path="/register"
          element={
            <GuestOnly>
              <RegisterPage />
            </GuestOnly>
          }
        />
        <Route element={<ProtectedLayout />}>
          <Route index element={<DashboardPage />} />
          <Route path="channels" element={<ChannelsPage />} />
          <Route path="favorites" element={<FavoritesPage />} />
          <Route path="guide" element={<GuidePage />} />
          <Route path="sources" element={<SourcesPage />} />
          <Route path="scan" element={<ScanPage />} />
          <Route path="settings" element={<SettingsPage />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Route>
      </Routes>
      <Toaster />
    </>
  );
}
