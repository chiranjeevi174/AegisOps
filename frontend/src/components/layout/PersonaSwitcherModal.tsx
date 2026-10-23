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
          <div className="p-3 bg-rose-950/60 border border-rose-800 rounded-lg text-xs text-rose-300">
            {errorMessage}
          </div>
        )}

        <div>
          <h4 className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2.5">
            Configured Development Personas
          </h4>
          {isLoadingActors ? (
            <p className="text-xs text-slate-500">Loading actors...</p>
          ) : isActorsDisabled || !actors || actors.length === 0 ? (
            <div className="p-3 bg-slate-900/80 border border-slate-800 rounded-lg text-xs text-slate-400">
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
                        ? "bg-indigo-950/50 border-indigo-600/70"
                        : "bg-slate-950/60 border-slate-800 hover:bg-slate-800/60"
                    }`}
                  >
                    <div className="flex items-center gap-3">
                      <div
                        className={`p-2 rounded-md ${
                          isCurrent ? "bg-indigo-600 text-white" : "bg-slate-800 text-slate-400"
                        }`}
                      >
                        <UserCheck className="w-4 h-4" />
                      </div>
                      <div>
                        <div className="flex items-center gap-2">
                          <span className="text-sm font-medium text-slate-200">
                            {actor.identity}
                          </span>
                          {isCurrent && (
                            <span className="text-[10px] font-semibold bg-indigo-500 text-white px-1.5 py-0.2 rounded">
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

        <div className="pt-3 border-t border-slate-800">
          <form onSubmit={handleTokenSubmit} className="space-y-3">
            <h4 className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
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
