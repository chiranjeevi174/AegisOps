import React, { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { authApi } from "@/services/api";
import { Modal } from "@/components/ui/Modal";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Badge } from "@/components/ui/Badge";
import { UserCheck, Key } from "lucide-react";

interface PersonaSwitcherModalProps {
  isOpen: boolean;
  onClose: () => void;
  currentIdentity?: string;
}

export const PersonaSwitcherModal: React.FC<PersonaSwitcherModalProps> = ({
  isOpen,
  onClose,
  currentIdentity,
}) => {
  const queryClient = useQueryClient();
  const [customToken, setCustomToken] = useState("");
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const { data: actors, isLoading: isLoadingActors, isError: isActorsDisabled } = useQuery({
    queryKey: ["auth", "actors"],
    queryFn: authApi.getActors,
    enabled: isOpen,
    retry: false,
  });

  const loginMutation = useMutation({
    mutationFn: authApi.loginSession,
    onSuccess: () => {
      setErrorMessage(null);
      setCustomToken("");
      queryClient.invalidateQueries({ queryKey: ["auth", "me"] });
      queryClient.invalidateQueries({ queryKey: ["overview"] });
      onClose();
    },
    onError: (err: any) => {
      setErrorMessage(err.message || "Authentication failed");
    },
  });

  const handleSelectActor = (identity: string) => {
    loginMutation.mutate({ identity });
  };

  const handleTokenSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!customToken.trim()) return;
    loginMutation.mutate({ token: customToken.trim() });
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title="Operator Persona & Authentication"
      description="Select a development persona or enter a valid bearer token to switch roles."
      maxWidth="md"
    >
      <div className="space-y-6">
        {errorMessage && (
          <div className="p-3 bg-rose-500/15 border border-status-critical/35 rounded-lg text-xs text-status-critical">
            {errorMessage}
          </div>
        )}

        <div>
          <h4 className="text-xs font-semibold text-obsidian-muted uppercase tracking-wider mb-2.5 font-mono">
            Configured Development Personas
          </h4>
          {isLoadingActors ? (
            <p className="text-xs text-obsidian-muted">Loading actors...</p>
          ) : isActorsDisabled || !actors || actors.length === 0 ? (
            <div className="p-3 bg-obsidian-900 border border-obsidian-700 rounded-lg text-xs text-obsidian-secondary">
              Development persona switching is disabled in this environment. Please authenticate using a valid bearer token below.
            </div>
          ) : (
            <div className="space-y-2">
              {actors?.map((actor) => {
                const isCurrent = actor.identity === currentIdentity;
                return (
                  <button
                    key={actor.identity}
                    onClick={() => handleSelectActor(actor.identity)}
                    disabled={loginMutation.isPending}
                    className={`w-full flex items-center justify-between p-3 rounded-lg border text-left transition-all ${
                      isCurrent
                        ? "bg-copper-400/10 border-copper-400/60 shadow-obsidian-sm"
                        : "bg-obsidian-900/80 border-obsidian-700 hover:bg-obsidian-750"
                    }`}
                  >
                    <div className="flex items-center gap-3">
                      <div
                        className={`p-2 rounded-md ${
                          isCurrent ? "bg-copper-400 text-obsidian-950 font-bold" : "bg-obsidian-750 text-obsidian-muted"
                        }`}
                      >
                        <UserCheck className="w-4 h-4" />
                      </div>
                      <div>
                        <div className="flex items-center gap-2">
                          <span className="text-xs font-semibold text-obsidian-text">
                            {actor.identity}
                          </span>
                          {isCurrent && (
                            <span className="text-[10px] font-bold font-mono bg-copper-400 text-obsidian-950 px-1.5 py-0.2 rounded">
                              ACTIVE
                            </span>
                          )}
                        </div>
                        <div className="flex flex-wrap gap-1 mt-1">
                          {actor.roles.map((role) => (
                            <Badge key={role} size="sm" variant="outline">
                              {role}
                            </Badge>
                          ))}
                        </div>
                      </div>
                    </div>
                  </button>
                );
              })}
            </div>
          )}
        </div>

        <div className="pt-3 border-t border-obsidian-700">
          <form onSubmit={handleTokenSubmit} className="space-y-3">
            <h4 className="text-xs font-semibold text-obsidian-muted uppercase tracking-wider font-mono">
              Or Authenticate with Token
            </h4>
            <div className="flex gap-2">
              <Input
                type="password"
                placeholder="Enter bearer token"
                value={customToken}
                onChange={(e) => setCustomToken(e.target.value)}
                disabled={loginMutation.isPending}
              />
              <Button
                type="submit"
                variant="secondary"
                disabled={!customToken.trim() || loginMutation.isPending}
                isLoading={loginMutation.isPending}
              >
                <Key className="w-4 h-4" />
                Apply
              </Button>
            </div>
          </form>
        </div>
      </div>
    </Modal>
  );
};
