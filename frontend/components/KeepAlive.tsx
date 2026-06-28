"use client";

import { useEffect } from "react";
import { api } from "@/lib/api";

/**
 * Pings the backend health endpoint on mount and every 4 minutes to keep a
 * free-tier (Render) instance warm and mask cold starts during a demo.
 */
export function KeepAlive() {
  useEffect(() => {
    const ping = () => api.health().catch(() => undefined);
    ping();
    const id = setInterval(ping, 4 * 60 * 1000);
    return () => clearInterval(id);
  }, []);
  return null;
}
