import { create } from "zustand";
interface AlertState {
  count: number;
  setCount: (n: number) => void;
}
export const useAlertStore = create<AlertState>(set => ({
  count: 0,
  setCount: n => set({ count: n }),
}));
