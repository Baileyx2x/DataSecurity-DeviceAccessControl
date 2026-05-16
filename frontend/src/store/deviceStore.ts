import { create } from "zustand";
import { Device } from "../api/devices";

interface DeviceState {
  devices: Device[];
  setDevices: (d: Device[]) => void;
}

export const useDeviceStore = create<DeviceState>(set => ({
  devices: [],
  setDevices: d => set({ devices: d }),
}));
