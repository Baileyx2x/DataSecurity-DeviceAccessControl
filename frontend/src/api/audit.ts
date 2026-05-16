import { api } from "./client";
export const listAudit = (limit=200) => api.get("/audit", { params: { limit } });
