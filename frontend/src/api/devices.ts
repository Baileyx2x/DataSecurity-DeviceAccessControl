import { api } from "./client";

export interface Device {
  id: number;
  mac: string;
  ip: string;
  hostname?: string;
  vendor?: string;
  category: "white" | "black" | "unknown";
  risk_level: number;
  status: "online" | "offline" | "blocked";
  last_seen: string;
}

export const listDevices    = (params?: Record<string, string>) => api.get<Device[]>("/devices", { params });
export const setWhitelist   = (id: number) => api.post(`/devices/${id}/whitelist`);
export const setBlacklist   = (id: number) => api.post(`/devices/${id}/blacklist`);
export const triggerScan    = () => api.post("/scan/trigger");
export const blockDevice    = (id: number, reason="manual") => api.post(`/blocker/${id}/block`, null, { params: { reason } });
export const unblockDevice  = (id: number, reason="manual") => api.post(`/blocker/${id}/unblock`, null, { params: { reason } });
