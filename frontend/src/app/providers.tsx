import React, { ReactNode, useState } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

interface AppProvidersProps {
  children: ReactNode;
}

export const AppProviders: React.FC<AppProvidersProps> = ({ children }) => {
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            refetchOnWindowFocus: false,
            retry: (failureCount, error: any) => {
              // Never retry 401, 403, 404
              if (error?.status === 401 || error?.status === 403 || error?.status === 404) {
                return false;
              }
              return failureCount < 1;
            },
            staleTime: 15000,
          },
          mutations: {
            retry: false, // Never automatically retry mutations
          },
        },
      })
  );

  return (
    <QueryClientProvider client={queryClient}>
      {children}
    </QueryClientProvider>
  );
};
