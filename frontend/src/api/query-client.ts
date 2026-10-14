import { QueryClient } from "@tanstack/react-query";

const STALE_TIME_MS = 5 * 60 * 1000;

export function createQueryClient() {
  return new QueryClient({
    defaultOptions: { queries: { staleTime: STALE_TIME_MS, retry: 1 } },
  });
}
