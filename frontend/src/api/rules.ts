import { api } from "./client";
export const listRules = () => api.get("/rules");
