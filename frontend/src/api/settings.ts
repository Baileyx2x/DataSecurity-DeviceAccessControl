import { api } from "./client";

export const getSettings = () => api.get("/settings");
export const updateSettings = (data: Record<string, string | number | boolean>) =>
  api.put("/settings", data);
