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
  first_seen: string;
  os_guess?: string;
  note?: string;
  alert_count?: number;
  access_count?: number;
  blocked_until?: string;
  block_schedule_start?: string;
  block_schedule_end?: string;
  blocked_by?: string;
  qos_down_kbps?: number;
  qos_up_kbps?: number;
}

export const listDevices    = (params?: Record<string, string>) => api.get<Device[]>("/devices", { params });
export const getDevice      = (id: number) => api.get<Device>(`/devices/${id}`);
export const getDeviceHistory = (id: number) => api.get(`/devices/${id}/history`);
export const getDeviceAlerts  = (id: number) => api.get(`/devices/${id}/alerts`);
export const getDeviceAudit   = (id: number) => api.get(`/devices/${id}/audit`);
export const setWhitelist   = (id: number) => api.post(`/devices/${id}/whitelist`);
export const setBlacklist   = (id: number) => api.post(`/devices/${id}/blacklist`);
export const setSchedule    = (id: number, data: { block_schedule_start: string; block_schedule_end: string }) =>
  api.put(`/devices/${id}/schedule`, data);
export const triggerScan    = () => api.post("/scan/trigger");
export const blockDevice    = (id: number, reason="manual") => api.post(`/blocker/${id}/block`, null, { params: { reason } });
export const unblockDevice  = (id: number, reason="manual") => api.post(`/blocker/${id}/unblock`, null, { params: { reason } });
export const limitBandwidth = (id: number, down_kbps: number, up_kbps: number) =>
  api.post(`/qos/${id}/limit`, { down_kbps, up_kbps });
export const unlimitBandwidth = (id: number) => api.post(`/qos/${id}/unlimit`);
export const deleteDevice = (id: number) => api.delete(`/devices/${id}`);
