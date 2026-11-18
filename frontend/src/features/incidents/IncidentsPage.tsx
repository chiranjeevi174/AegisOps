import React, { useState, useMemo } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import * as z from "zod";
import {
  AlertTriangle,
  Plus,
  Search,
  Clock,
  Radio,
} from "lucide-react";
import { incidentsApi } from "@/services/api";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Input, Select } from "@/components/ui/Input";
import { Modal } from "@/components/ui/Modal";
import { EmptyState, Skeleton } from "@/components/ui/Feedback";

const createIncidentSchema = z.object({
  title: z.string().min(3, "Title must be at least 3 characters").max(200),
  description: z.string().min(5, "Description must be at least 5 characters"),
  severity: z.enum(["critical", "high", "medium", "low"]),
});

type CreateIncidentFormValues = z.infer<typeof createIncidentSchema>;

export const IncidentsPage: React.FC = () => {
  const queryClient = useQueryClient();
  const [searchTerm, setSearchTerm] = useState("");
  const [severityFilter, setSeverityFilter] = useState<string>("all");
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);

  const { data: incidents, isLoading, isError, error } = useQuery({
    queryKey: ["incidents"],
    queryFn: () => incidentsApi.list(100, 0),
  });

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<CreateIncidentFormValues>({
    resolver: zodResolver(createIncidentSchema),
    defaultValues: {
      severity: "high",
    },
  });

  const createMutation = useMutation({
    mutationFn: incidentsApi.create,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["incidents"] });
      queryClient.invalidateQueries({ queryKey: ["overview"] });
      setIsCreateModalOpen(false);
      reset();
    },
  });

  const filteredIncidents = useMemo(() => {
    if (!incidents) return [];
    return incidents.filter((inc) => {
      const matchesSearch =
        inc.title.toLowerCase().includes(searchTerm.toLowerCase()) ||
        inc.description.toLowerCase().includes(searchTerm.toLowerCase()) ||
        inc.id.toLowerCase().includes(searchTerm.toLowerCase());
      const matchesSeverity =
        severityFilter === "all" || inc.severity === severityFilter;
      const matchesStatus =
        statusFilter === "all" || inc.status === statusFilter;
      return matchesSearch && matchesSeverity && matchesStatus;
    });
  }, [incidents, searchTerm, severityFilter, statusFilter]);

  const onSubmit = (data: CreateIncidentFormValues) => {
    createMutation.mutate(data);
  };

  return (
    <div className="space-y-6 text-obsidian-text">
      {/* Header and Actions */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-obsidian-text tracking-tight flex items-center gap-2">
            <AlertTriangle className="w-5 h-5 text-copper-400" />
            Incident Management
          </h1>
          <p className="text-xs text-obsidian-muted mt-1">
            Monitor, investigate, and triage production alert streams and incidents with immutable audit tracking.
          </p>
        </div>
        <Button onClick={() => setIsCreateModalOpen(true)}>
          <Plus className="w-4 h-4" />
          Create Incident
        </Button>
      </div>

      {/* Filter and Search Bar */}
      <Card className="bg-obsidian-800 border-obsidian-700">
        <CardContent className="p-3.5">
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            <div className="relative">
              <Search className="w-4 h-4 text-obsidian-muted absolute left-3 top-2.5" />
              <input
                type="text"
                placeholder="Search title, description, or UUID..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="w-full pl-9 pr-3 py-2 bg-obsidian-900 border border-obsidian-700 rounded-lg text-xs text-obsidian-text placeholder-obsidian-muted focus:outline-none focus:ring-1 focus:ring-copper-400 focus:border-copper-400 transition-colors"
              />
            </div>
            <select
              value={severityFilter}
              onChange={(e) => setSeverityFilter(e.target.value)}
              className="px-3 py-2 bg-obsidian-900 border border-obsidian-700 rounded-lg text-xs text-obsidian-text focus:outline-none focus:ring-1 focus:ring-copper-400 focus:border-copper-400 transition-colors"
            >
              <option value="all">All Severities</option>
              <option value="critical">Critical (P1)</option>
              <option value="high">High (P2)</option>
              <option value="medium">Medium (P3)</option>
              <option value="low">Low (P4)</option>
            </select>
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="px-3 py-2 bg-obsidian-900 border border-obsidian-700 rounded-lg text-xs text-obsidian-text focus:outline-none focus:ring-1 focus:ring-copper-400 focus:border-copper-400 transition-colors"
            >
              <option value="all">All Statuses</option>
              <option value="open">Open</option>
              <option value="investigating">Investigating</option>
              <option value="resolved">Resolved</option>
            </select>
          </div>
        </CardContent>
      </Card>

      {/* Incidents Table */}
      <Card className="bg-obsidian-800 border-obsidian-700">
        <CardHeader className="py-3 px-4 flex flex-row items-center justify-between border-b border-obsidian-700">
          <div className="flex items-center gap-2">
            <CardTitle>Recorded Incidents</CardTitle>
            <span className="text-xs px-2 py-0.5 rounded-full bg-obsidian-900 border border-obsidian-700 text-copper-300 font-mono font-semibold">
              {filteredIncidents.length}
            </span>
          </div>
        </CardHeader>
        <CardContent className="p-0">
          {isLoading ? (
            <div className="p-6 space-y-3">
              <Skeleton className="h-10 w-full bg-obsidian-750" />
              <Skeleton className="h-10 w-full bg-obsidian-750" />
              <Skeleton className="h-10 w-full bg-obsidian-750" />
            </div>
          ) : isError ? (
            <div className="p-6 text-center text-status-critical text-xs">
              Failed to load incidents: {(error as any)?.message}
            </div>
          ) : filteredIncidents.length === 0 ? (
            <EmptyState
              title="No Incidents Match Filter"
              description="Try adjusting your search query or severity/status filter."
            />
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead className="bg-obsidian-900 border-b border-obsidian-700 text-obsidian-muted font-semibold uppercase tracking-wider font-mono text-[11px]">
                  <tr>
                    <th className="py-3 px-4">Severity</th>
                    <th className="py-3 px-4">Title & Context</th>
                    <th className="py-3 px-4">Status</th>
                    <th className="py-3 px-4">Source</th>
                    <th className="py-3 px-4">Alert State</th>
                    <th className="py-3 px-4">Created Time</th>
                    <th className="py-3 px-4 text-right">Action</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-obsidian-700/60 font-sans">
                  {filteredIncidents.map((incident) => (
                    <tr
                      key={incident.id}
                      className="hover:bg-obsidian-750/50 transition-colors group"
                    >
                      <td className="py-3 px-4 whitespace-nowrap">
                        <Badge variant={incident.severity}>
                          {incident.severity.toUpperCase()}
                        </Badge>
                      </td>
                      <td className="py-3 px-4">
                        <Link
                          to={`/incidents/${incident.id}`}
                          className="font-medium text-obsidian-text group-hover:text-copper-400 transition-colors block"
                        >
                          {incident.title}
                        </Link>
                        <span className="text-[11px] font-mono text-obsidian-muted truncate block max-w-xs mt-0.5">
                          {incident.id}
                        </span>
                      </td>
                      <td className="py-3 px-4 whitespace-nowrap">
                        <Badge
                          variant={
                            incident.status === "open"
                              ? "high"
                              : incident.status === "investigating"
                              ? "info"
                              : "low"
                          }
                        >
                          {incident.status.toUpperCase()}
                        </Badge>
                      </td>
                      <td className="py-3 px-4 whitespace-nowrap text-obsidian-secondary font-mono text-[11px]">
                        {incident.source}
                      </td>
                      <td className="py-3 px-4 whitespace-nowrap">
                        {incident.alert_state ? (
                          <span className="inline-flex items-center gap-1.5 text-[11px] text-status-warning font-mono">
                            <Radio className="w-3 h-3 text-status-warning" />
                            {incident.alert_state}
                          </span>
                        ) : (
                          <span className="text-obsidian-muted">—</span>
                        )}
                      </td>
                      <td className="py-3 px-4 whitespace-nowrap text-obsidian-muted font-mono text-[11px]">
                        <div className="flex items-center gap-1.5">
                          <Clock className="w-3.5 h-3.5 text-obsidian-muted" />
                          <span>{new Date(incident.created_at).toLocaleString()}</span>
                        </div>
                      </td>
                      <td className="py-3 px-4 text-right whitespace-nowrap">
                        <Link to={`/incidents/${incident.id}`}>
                          <Button variant="secondary" size="sm">
                            Inspect
                          </Button>
                        </Link>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Create Incident Modal */}
      <Modal
        isOpen={isCreateModalOpen}
        onClose={() => setIsCreateModalOpen(false)}
        title="Create New Incident"
        description="Manually record an operational degradation or service incident."
      >
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          <Input
            label="Incident Title"
            placeholder="e.g. Database connection pool exhaustion"
            {...register("title")}
            error={errors.title?.message}
          />
          <div>
            <label className="block text-xs font-medium text-obsidian-secondary mb-1">
              Description
            </label>
            <textarea
              rows={3}
              placeholder="Detailed description of symptoms, error logs, or user impact..."
              {...register("description")}
              className={`w-full px-3.5 py-2 bg-obsidian-900 border rounded-lg text-xs text-obsidian-text placeholder-obsidian-muted focus:outline-none focus:ring-1 focus:ring-copper-400 focus:border-copper-400 ${
                errors.description ? "border-status-critical" : "border-obsidian-700"
              }`}
            />
            {errors.description && (
              <p className="text-xs text-status-critical mt-1">{errors.description.message}</p>
            )}
          </div>
          <Select
            label="Severity"
            {...register("severity")}
            error={errors.severity?.message}
            options={[
              { value: "critical", label: "Critical (P1 — Outage / Data Integrity)" },
              { value: "high", label: "High (P2 — Degraded User Service)" },
              { value: "medium", label: "Medium (P3 — Non-critical Component Failure)" },
              { value: "low", label: "Low (P4 — Advisory / Cosmetic)" },
            ]}
          />
          <div className="flex justify-end gap-2 pt-3 border-t border-obsidian-700">
            <Button
              type="button"
              variant="ghost"
              onClick={() => setIsCreateModalOpen(false)}
            >
              Cancel
            </Button>
            <Button
              type="submit"
              variant="primary"
              isLoading={createMutation.isPending}
            >
              Submit Incident
            </Button>
          </div>
        </form>
      </Modal>
    </div>
  );
};
