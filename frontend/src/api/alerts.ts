import { api } from "./client";
export const listAlerts = (status?: string) => api.get("/alerts", { params: status ? { status } : {} });
export const ackAlert   = (id: number) => api.post(`/alerts/${id}/ack`);
