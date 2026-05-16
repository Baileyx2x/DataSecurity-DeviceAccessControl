import { useEffect } from "react";

export function usePolling(fn: () => void, intervalMs = 5000) {
  useEffect(() => {
    fn();
    const t = setInterval(fn, intervalMs);
    return () => clearInterval(t);
  }, []);
}
