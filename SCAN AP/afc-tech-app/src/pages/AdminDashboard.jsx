import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useTenant } from "../context/TenantContext";

const API_BASE =
  import.meta.env.VITE_API_BASE_URL ||
  (import.meta.env.DEV ? "http://127.0.0.1:5000" : "");

async function safeReadJson(response, defaultValue) {
  const raw = await response.text();
  if (!raw) return defaultValue;
  try {
    return JSON.parse(raw);
  } catch {
    return defaultValue;
  }
}

export default function AdminDashboard() {
  const navigate = useNavigate();
  const { config } = useTenant();
  const terms = config.terminology;
  const [stats, setStats] = useState({});

  useEffect(() => {
    const fetchStats = async () => {
      try {
        const response = await fetch(`${API_BASE}/api/admin/stats`, {
          headers: {
            "X-Tenant-ID": String(config.tenantId || 1),
          },
        });
        if (response.ok) {
          const data = await safeReadJson(response, {});
          setStats(data);
        }
      } catch (err) {
        console.error("Stats endpoint not yet available:", err);
      }
    };
    fetchStats();
  }, [config.tenantId]);

  return (
    <div data-theme="corporate" className="min-h-screen flex flex-col bg-base-200">
      {/* Header */}
      <header className="navbar bg-base-100 shadow-sm px-4">
        <div className="flex-1">
          <button className="btn btn-ghost btn-sm" onClick={() => navigate("/")}>
            ← Back to Home
          </button>
          <span className="font-bold text-lg ml-2">Admin Dashboard</span>
        </div>
      </header>

      {/* Main Content */}
      <main className="flex-1 px-4 pt-4 pb-10 max-w-4xl mx-auto w-full">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* Stats Cards */}
            <div className="card bg-base-100 shadow-sm border border-base-300">
              <div className="card-body">
                <h2 className="card-title text-sm">{terms.location_plural}</h2>
                <div className="text-3xl font-bold text-primary">{stats.locations_count || 0}</div>
              </div>
            </div>

            <div className="card bg-base-100 shadow-sm border border-base-300">
              <div className="card-body">
                <h2 className="card-title text-sm">{terms.asset_plural}</h2>
                <div className="text-3xl font-bold text-primary">{stats.assets_count || 0}</div>
              </div>
            </div>

            <div className="card bg-base-100 shadow-sm border border-base-300">
              <div className="card-body">
                <h2 className="card-title text-sm">Service Jobs</h2>
                <div className="text-3xl font-bold text-success">{stats.jobs_count || 0}</div>
              </div>
            </div>

            <div className="card bg-base-100 shadow-sm border border-base-300">
              <div className="card-body">
                <h2 className="card-title text-sm">Pending Tasks</h2>
                <div className="text-3xl font-bold text-warning">{stats.pending_tasks || 0}</div>
              </div>
            </div>

            {/* Admin Actions */}
            <div className="card bg-base-100 shadow-sm border border-base-300 md:col-span-2">
              <div className="card-body">
                <h2 className="card-title text-base mb-4">Quick Actions</h2>
                <div className="space-y-2">
                  <button className="btn btn-outline btn-block" disabled>
                    📊 View Reports (Coming Soon)
                  </button>
                  <button className="btn btn-outline btn-block" disabled>
                    👥 Manage Technicians (Coming Soon)
                  </button>
                  <button className="btn btn-outline btn-block" disabled>
                    ⚙️ System Settings (Coming Soon)
                  </button>
                </div>
              </div>
            </div>

            {/* API Status */}
            <div className="card bg-base-100 shadow-sm border border-base-300 md:col-span-2">
              <div className="card-body">
                <h2 className="card-title text-base mb-2">System Health</h2>
                <div className="badge badge-success">✓ Backend Connected</div>
                <div className="badge badge-info">Tenant: {config.tenantName}</div>
                {config.industry && <div className="badge badge-ghost">Industry: {config.industry}</div>}
              </div>
            </div>
          </div>
      </main>
    </div>
  );
}
