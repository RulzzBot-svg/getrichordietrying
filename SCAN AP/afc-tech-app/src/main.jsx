// main.jsx
import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import App from "./App";
import "./index.css";
import QRScanner from "./components/common/QRScanner";
import AssetScanPage from "./pages/AssetScanPage";
import LocationAssetBrowser from "./pages/LocationAssetBrowser";
import AdminDashboard from "./pages/AdminDashboard";
import { TenantProvider } from "./context/TenantContext";

ReactDOM.createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    {/*
      TenantProvider wraps the entire app so that every component can access
      the tenant's brand colour, logo, and terminology dictionary via useTenant().
    */}
    <TenantProvider>
      <BrowserRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
        <Routes>
          <Route path="/" element={<App />} />
          <Route path="/Home" element={<App />} />
          <Route path="/scan" element={<QRScanner />} />
          {/* Manual location/asset browser — fallback when QR not available */}
          <Route path="/hospitals" element={<LocationAssetBrowser />} />
          {/* Universal asset scan page — opened by /scan?asset_id=<id> QR codes */}
          <Route path="/asset-scan" element={<AssetScanPage />} />
          {/* Admin dashboard — for admins only */}
          <Route path="/admin" element={<AdminDashboard />} />
        </Routes>
      </BrowserRouter>
    </TenantProvider>
  </React.StrictMode>
);
