// main.jsx
import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import App from "./App";
import HospitalCards from "./components/common/HospitalCards";
import AHU from "./components/common/AHU";
import FilterInfo from "./components/common/FilterInfo";
import AHUPage from "./components/common/AHUPage";
import BuildingsPage from "./components/common/BuildingsPage";
import jobCompleted from "./components/common/job-completed";
import "./index.css";
import QRScanner from "./components/common/QRScanner";
import AdminDashboard from "./components/admin/admin";
import Hospitals from "./components/admin/hospitals";
import AdminAHUs from "./components/admin/adminahus";
import AdminJobs from "./components/admin/adminjobs";
import AdminSignoffs from "./components/admin/AdminSignoffs";
import AdminLayout from "./components/admin/AdminLayout";
import Login from "./components/common/login";
import JobSignature from "./components/common/jobSignatures";
import SummaryExample from "./pages/SummaryExample";
import TechSignoff from "./pages/TechSignoff";
import AssetScanPage from "./pages/AssetScanPage";
import { TenantProvider } from "./context/TenantContext";

if (import.meta.env.PROD) {
  import("virtual:pwa-register").then(({ registerSW }) => {
    registerSW({ immediate: true });
  });
}

ReactDOM.createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    {/*
      TenantProvider wraps the entire app so that every component can access
      the tenant's brand colour, logo, and terminology dictionary via useTenant().
    */}
    <TenantProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<Login />} />
          <Route path="/login" element={<Login />} />
          <Route path="/Home" element={<App />} />
          <Route path="/hospitals" element={<HospitalCards />} />
          <Route path="/buildings/:hospitalId" element={<BuildingsPage />} />
          <Route path="/AHU" element={<AHU />} />
          <Route path="/AHU/:hospitalId" element={<AHUPage />} />
          <Route path="/AHU/:hospitalId/building/:buildingId" element={<AHUPage />} />
          <Route path="/FilterInfo/:ahuId" element={<FilterInfo />} />
          <Route path="/job-completed" element={<jobCompleted />} />
          <Route path="/scan" element={<QRScanner />} />
          {/* Universal asset scan page — opened by /scan?asset_id=<id> QR codes */}
          <Route path="/asset-scan" element={<AssetScanPage />} />
          <Route path="/jobs/:jobId/signature" element={<JobSignature />} />
          <Route path="/admin" element={<AdminLayout />}>
            <Route index element={<AdminDashboard />} />
            <Route path="hospitals" element={<Hospitals />} />
            <Route path="ahus" element={<AdminAHUs />} />
            <Route path="jobs" element={<AdminJobs />} />
            <Route path="signoffs" element={<AdminSignoffs />} />
          </Route>

          {import.meta.env.DEV ? (
            <Route path="/dev/summary" element={<SummaryExample />} />
          ) : null}

          <Route path="/tech/signoff" element={<TechSignoff />} />
        </Routes>
      </BrowserRouter>
    </TenantProvider>
  </React.StrictMode>
);
