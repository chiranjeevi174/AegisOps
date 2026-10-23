import React, { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  History,
  Search,
  Eye,
} from "lucide-react";
import { auditApi } from "@/services/api";
import type { UnifiedAuditEvent } from "@/types/audit";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { Modal } from "@/components/ui/Modal";
import { Button } from "@/components/ui/Button";
import { EmptyState, Skeleton } from "@/components/ui/Feedback";

export const AuditHistoryPage: React.FC = () => {
  const [categoryFilter, setCategoryFilter] = useState<string>("all");
  const [searchTerm, setSearchTerm] = useState("");
  const [selectedEvent, setSelectedEvent] = useState<UnifiedAuditEvent | null>(null);

  const { data: events, isLoading } = useQuery({
    queryKey: ["audit", "events", categoryFilter],
    queryFn: () => auditApi.getEvents({ category: categoryFilter, limit: 100 }),
  });

  const filteredEvents = (events || []).filter((ev) => {
    const term = searchTerm.toLowerCase();
    return (
      ev.event_type.toLowerCase().includes(term) ||
      ev.actor.toLowerCase().includes(term) ||
      ev.resource_id.toLowerCase().includes(term) ||
      (ev.incident_id && ev.incident_id.toLowerCase().includes(term))
    );
  });

  const getCategoryBadge = (cat: UnifiedAuditEvent["category"]) => {
    switch (cat) {
      case "approval":
        return <Badge variant="high">APPROVAL</Badge>;
      case "execution":
        return <Badge variant="primary">EXECUTION</Badge>;
      case "verification":
        return <Badge variant="info">VERIFICATION</Badge>;
      case "rollback":
        return <Badge variant="secondary">ROLLBACK</Badge>;
      default:
        return <Badge variant="outline">{cat}</Badge>;
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-slate-100 tracking-tight flex items-center gap-2">
            <History className="w-5 h-5 text-indigo-400" />
            Platform Immutable Audit Trail
          </h1>
          <p className="text-xs text-slate-400 mt-1">
            Tamper-resistant append-only event log capturing every approval decision, execution run, verification check, and rollback evaluation.
          </p>
        </div>

        {/* Category Tabs */}
        <div className="flex flex-wrap gap-1 p-1 bg-slate-900 border border-slate-800 rounded-lg text-xs">
          {["all", "approval", "execution", "verification", "rollback"].map((cat) => (
            <button
              key={cat}
              onClick={() => setCategoryFilter(cat)}
              className={`px-3 py-1.5 rounded-md font-medium transition-colors ${
                categoryFilter === cat
                  ? "bg-indigo-600 text-white"
                  : "text-slate-400 hover:text-slate-200"
              }`}
            >
              {cat.toUpperCase()}
            </button>
          ))}
        </div>
      </div>

      {/* Search Filter */}
      <Card>
        <CardContent className="p-3">
          <div className="relative">
            <Search className="w-4 h-4 text-slate-500 absolute left-3 top-2.5" />
            <input
              type="text"
              placeholder="Search by event type, actor identity, or resource UUID..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full pl-9 pr-3 py-2 bg-slate-950 border border-slate-800 rounded-lg text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-indigo-500"
            />
          </div>
        </CardContent>
      </Card>

      {/* Events Table */}
      <Card>
        <CardHeader className="py-3 px-4">
          <CardTitle className="text-sm flex items-center gap-2">
            <span>Audit Events</span>
            <span className="text-xs font-mono text-slate-500">
              ({filteredEvents.length})
            </span>
          </CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          {isLoading ? (
            <div className="p-6 space-y-3">
              <Skeleton className="h-10" />
              <Skeleton className="h-10" />
            </div>
          ) : filteredEvents.length === 0 ? (
            <EmptyState
              title="No Audit Events Found"
              description="No audit records match the current category and search criteria."
            />
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead className="bg-slate-950/70 border-b border-slate-800 text-slate-400 font-semibold uppercase tracking-wider">
                  <tr>
                    <th className="py-3 px-4">Category</th>
                    <th className="py-3 px-4">Event Type</th>
                    <th className="py-3 px-4">Actor</th>
                    <th className="py-3 px-4">Status Transition</th>
                    <th className="py-3 px-4">Resource UUID</th>
                    <th className="py-3 px-4">Timestamp</th>
                    <th className="py-3 px-4 text-right">Details</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/60 font-mono">
                  {filteredEvents.map((ev) => (
                    <tr key={ev.id} className="hover:bg-slate-800/40 transition-colors">
                      <td className="py-3 px-4 whitespace-nowrap">
                        {getCategoryBadge(ev.category)}
                      </td>
                      <td className="py-3 px-4 font-sans font-semibold text-indigo-300">
                        {ev.event_type}
                      </td>
                      <td className="py-3 px-4 font-sans text-slate-200">{ev.actor}</td>
                      <td className="py-3 px-4 text-slate-400">
                        {ev.previous_status ? (
                          <span>
                            {ev.previous_status} &rarr;{" "}
                            <strong className="text-slate-200">{ev.new_status}</strong>
                          </span>
                        ) : (
                          <strong className="text-slate-200">{ev.new_status || "—"}</strong>
                        )}
                      </td>
                      <td className="py-3 px-4 text-slate-500">{ev.resource_id.slice(0, 8)}...</td>
                      <td className="py-3 px-4 font-sans text-slate-400">
                        {new Date(ev.created_at).toLocaleString()}
                      </td>
                      <td className="py-3 px-4 text-right">
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => setSelectedEvent(ev)}
                        >
                          <Eye className="w-3.5 h-3.5" />
                          View
                        </Button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Event Details Modal */}
      {selectedEvent && (
        <Modal
          isOpen={!!selectedEvent}
          onClose={() => setSelectedEvent(null)}
          title={`Audit Event: ${selectedEvent.event_type}`}
          description={`Logged at ${new Date(selectedEvent.created_at).toISOString()}`}
          maxWidth="md"
        >
          <div className="space-y-3 text-xs">
            <div className="p-3 bg-slate-950 rounded-lg border border-slate-800 space-y-1.5 font-mono">
              <div className="flex justify-between">
                <span className="text-slate-500">Category:</span>
                <span className="text-indigo-400 uppercase">{selectedEvent.category}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-500">Actor:</span>
                <span className="text-slate-200">{selectedEvent.actor}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-500">Resource ID:</span>
                <span className="text-slate-300">{selectedEvent.resource_id}</span>
              </div>
              {selectedEvent.incident_id && (
                <div className="flex justify-between">
                  <span className="text-slate-500">Incident ID:</span>
                  <span className="text-slate-300">{selectedEvent.incident_id}</span>
                </div>
              )}
            </div>

            <div className="p-3 bg-slate-950 rounded-lg border border-slate-800 space-y-1">
              <span className="font-semibold text-slate-300 block mb-1">Sanitized Details:</span>
              <pre className="p-2.5 bg-slate-900 rounded border border-slate-800 font-mono text-emerald-300 text-[11px] overflow-x-auto">
                {JSON.stringify(selectedEvent.details, null, 2)}
              </pre>
            </div>
          </div>
        </Modal>
      )}
    </div>
  );
};
