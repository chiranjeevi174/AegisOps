import React, { Suspense } from "react";
import { Routes, Route, Navigate } from "react-router-dom";
import { AppLayout } from "@/components/layout/AppLayout";
import { Skeleton } from "@/components/ui/Feedback";

// Route-level code splitting for production bundle optimization
const DashboardPage = React.lazy(() =>
  import("@/features/dashboard/DashboardPage").then((m) => ({ default: m.DashboardPage }))
);
const IncidentsPage = React.lazy(() =>
  import("@/features/incidents/IncidentsPage").then((m) => ({ default: m.IncidentsPage }))
);
const IncidentDetailPage = React.lazy(() =>
  import("@/features/incidents/IncidentDetailPage").then((m) => ({ default: m.IncidentDetailPage }))
);
const InvestigationPage = React.lazy(() =>
  import("@/features/investigation/InvestigationPage").then((m) => ({ default: m.InvestigationPage }))
);
const RemediationPlansPage = React.lazy(() =>
  import("@/features/remediation/RemediationPlansPage").then((m) => ({ default: m.RemediationPlansPage }))
);
const ApprovalsPage = React.lazy(() =>
  import("@/features/approvals/ApprovalsPage").then((m) => ({ default: m.ApprovalsPage }))
);
const ExecutionsPage = React.lazy(() =>
  import("@/features/executions/ExecutionsPage").then((m) => ({ default: m.ExecutionsPage }))
);
const VerificationsPage = React.lazy(() =>
  import("@/features/verifications/VerificationsPage").then((m) => ({ default: m.VerificationsPage }))
);
const RollbacksPage = React.lazy(() =>
  import("@/features/rollbacks/RollbacksPage").then((m) => ({ default: m.RollbacksPage }))
);
const AuditHistoryPage = React.lazy(() =>
  import("@/features/audit/AuditHistoryPage").then((m) => ({ default: m.AuditHistoryPage }))
);
const SettingsPage = React.lazy(() =>
  import("@/features/settings/SettingsPage").then((m) => ({ default: m.SettingsPage }))
);

const RouteLoadingFallback: React.FC = () => (
  <div className="p-6 space-y-4 max-w-7xl mx-auto" role="status" aria-label="Loading page">
    <Skeleton className="h-8 w-64 bg-slate-800/80" />
    <Skeleton className="h-32 w-full bg-slate-850/80" />
    <Skeleton className="h-72 w-full bg-slate-850/80" />
  </div>
);

export const AppRouter: React.FC = () => {
  return (
    <Suspense fallback={<RouteLoadingFallback />}>
      <Routes>
        <Route path="/" element={<AppLayout />}>
          <Route index element={<DashboardPage />} />
          <Route path="incidents" element={<IncidentsPage />} />
          <Route path="incidents/:id" element={<IncidentDetailPage />} />
          <Route path="investigations" element={<InvestigationPage />} />
          <Route path="remediation" element={<RemediationPlansPage />} />
          <Route path="approvals" element={<ApprovalsPage />} />
          <Route path="executions" element={<ExecutionsPage />} />
          <Route path="verifications" element={<VerificationsPage />} />
          <Route path="rollbacks" element={<RollbacksPage />} />
          <Route path="audit" element={<AuditHistoryPage />} />
          <Route path="settings" element={<SettingsPage />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Route>
      </Routes>
    </Suspense>
  );
};
