import { Routes, Route } from "react-router-dom";
import Dashboard from "./pages/Dashboard";
import DeviceList from "./pages/Devices/DeviceList";
import Alerts from "./pages/Alerts";
import Rules from "./pages/Rules";
import Audit from "./pages/Audit";
import Settings from "./pages/Settings";

export function AppRouter() {
  return (
    <Routes>
      <Route path="/"         element={<Dashboard />} />
      <Route path="/devices"  element={<DeviceList />} />
      <Route path="/alerts"   element={<Alerts />} />
      <Route path="/rules"    element={<Rules />} />
      <Route path="/audit"    element={<Audit />} />
      <Route path="/settings" element={<Settings />} />
    </Routes>
  );
}
