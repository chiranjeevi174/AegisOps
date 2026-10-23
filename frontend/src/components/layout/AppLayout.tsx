import React, { useState } from "react";
import { Outlet } from "react-router-dom";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { authApi, overviewApi } from "@/services/api";
import { Sidebar } from "@/components/layout/Sidebar";
import { Header } from "@/components/layout/Header";
import { PersonaSwitcherModal } from "@/components/layout/PersonaSwitcherModal";

export const AppLayout: React.FC = () => {
  const [isPersonaModalOpen, setIsPersonaModalOpen] = useState(false);
  const queryClient = useQueryClient();

  // Load current user profile (from HttpOnly session cookie or development default)
  const { data: actor } = useQuery({
    queryKey: ["auth", "me"],
    queryFn: async () => {
      try {
        return await authApi.getMe();
      } catch {
        // In local dev, auto-login with sre-operator-dan session if persona switching is permitted
        try {
          return await authApi.loginSession({ identity: "sre-operator-dan" });
        } catch {
          return undefined;
        }
      }
    },
    staleTime: 60000,
  });

  // Load overview for header & sidebar counts
  const { data: overview, isRefetching, refetch } = useQuery({
    queryKey: ["overview"],
    queryFn: overviewApi.getOverview,
    staleTime: 30000,
  });

  const handleRefresh = () => {
    refetch();
    queryClient.invalidateQueries();
  };

  return (
    <div className="flex h-screen bg-slate-950 text-slate-100 overflow-hidden font-sans">
      <Sidebar
        actor={actor}
        onOpenPersonaModal={() => setIsPersonaModalOpen(true)}
        openIncidentsCount={overview?.open_incidents}
        pendingApprovalsCount={overview?.pending_approvals}
      />

      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        <Header
          actor={actor}
          monitoringAvailable={overview?.monitoring_available}
          onRefresh={handleRefresh}
          isRefreshing={isRefetching}
        />

        <main className="flex-1 overflow-y-auto p-6 space-y-6">
          <Outlet context={{ actor, overview }} />
        </main>
      </div>

      <PersonaSwitcherModal
        isOpen={isPersonaModalOpen}
        onClose={() => setIsPersonaModalOpen(false)}
        currentIdentity={actor?.identity}
      />
    </div>
  );
};
