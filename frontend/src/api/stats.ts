import { api } from "./client";

export const getTimeline = () => api.get("/stats/timeline");
export const getOverview = () => api.get("/stats/overview");
export const getDeviceTraffic = (id: number) => api.get(`/stats/traffic/${id}`);
