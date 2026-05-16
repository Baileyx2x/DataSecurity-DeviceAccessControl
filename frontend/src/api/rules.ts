import { api } from "./client";

export interface Rule {
  id: number;
  name: string;
  description: string;
  condition_json: string;
  action: "alert" | "block";
  level: number;
  enabled: boolean;
}

export const listRules = () => api.get<Rule[]>("/rules");
export const createRule = (data: Partial<Rule>) => api.post("/rules", data);
export const updateRule = (id: number, data: Partial<Rule>) => api.put(`/rules/${id}`, data);
export const deleteRule = (id: number) => api.delete(`/rules/${id}`);
export const toggleRule = (id: number) => api.post(`/rules/${id}/toggle`);
