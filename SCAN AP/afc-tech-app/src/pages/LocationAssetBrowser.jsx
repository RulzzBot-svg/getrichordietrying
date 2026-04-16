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
    throw new Error("Server returned non-JSON data. Check frontend API base URL.");
  }
}

export default function LocationAssetBrowser() {
  const navigate = useNavigate();
  const { config } = useTenant();
  const terms = config.terminology;

  const [locations, setLocations] = useState([]);
  const [assets, setAssets] = useState([]);
  const [selectedLocation, setSelectedLocation] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Fetch locations on mount
  useEffect(() => {
    const fetchLocations = async () => {
      try {
        setLoading(true);
        const response = await fetch(`${API_BASE}/api/locations`, {
          headers: {
            "X-Tenant-ID": String(config.tenantId || 1),
          },
        });
        if (response.ok) {
          const data = await safeReadJson(response, []);
          setLocations(data || []);
        } else {
          const errData = await safeReadJson(response, {});
          setError(errData.error || "Failed to load locations");
        }
      } catch (err) {
        setError(err.message || "Error loading locations");
      } finally {
        setLoading(false);
      }
    };
    fetchLocations();
  }, [config.tenantId]);

  // Fetch assets when location changes
  useEffect(() => {
    if (selectedLocation) {
      const fetchAssets = async () => {
        try {
          const response = await fetch(
            `${API_BASE}/api/locations/${selectedLocation}/assets`,
            {
              headers: {
                "X-Tenant-ID": String(config.tenantId || 1),
              },
            }
          );
          if (response.ok) {
            const data = await safeReadJson(response, []);
            setAssets(data || []);
          } else {
            setAssets([]);
          }
        } catch (err) {
          setAssets([]);
        }
      };
      fetchAssets();
    }
  }, [selectedLocation, config.tenantId]);

  const handleAssetClick = (asset) => {
    // Navigate to asset scan page with asset_id
    navigate(`/asset-scan?asset_id=${asset.id}`);
  };

  return (
    <div data-theme="corporate" className="min-h-screen flex flex-col bg-base-200">
      {/* Header */}
      <header className="navbar bg-base-100 shadow-sm px-4">
        <div className="flex-1">
          <button className="btn btn-ghost btn-sm" onClick={() => navigate("/")}>
            ← Back
          </button>
          <span className="font-bold text-lg ml-2">Select {terms.asset_name}</span>
        </div>
      </header>

      {/* Main Content */}
      <main className="flex-1 px-4 pt-4 pb-10 max-w-2xl mx-auto w-full">
        {loading ? (
          <div className="flex justify-center items-center h-32">
            <span className="loading loading-spinner loading-lg"></span>
          </div>
        ) : error ? (
          <div className="alert alert-error">
            <span>{error}</span>
            <button className="btn btn-sm btn-ghost" onClick={() => window.location.reload()}>
              Retry
            </button>
          </div>
        ) : (
          <div className="space-y-4">
            {/* Location Select */}
            <div className="card bg-base-100 shadow-sm border border-base-300">
              <div className="card-body">
                <h2 className="card-title text-base">
                  Choose a {terms.location_name}
                </h2>
                <select
                  className="select select-bordered w-full"
                  value={selectedLocation || ""}
                  onChange={(e) => setSelectedLocation(e.target.value ? parseInt(e.target.value) : null)}
                >
                  <option value="">-- Select {terms.location_name} --</option>
                  {locations.map((loc) => (
                    <option key={loc.id} value={loc.id}>
                      {loc.name}
                    </option>
                  ))}
                </select>
              </div>
            </div>

            {/* Asset List */}
            {selectedLocation && (
              <div className="card bg-base-100 shadow-sm border border-base-300">
                <div className="card-body">
                  <h2 className="card-title text-base">
                    {terms.asset_plural} in this {terms.location_name.toLowerCase()}
                  </h2>
                  {assets.length === 0 ? (
                    <p className="text-base-content/70">No {terms.asset_plural.toLowerCase()} found.</p>
                  ) : (
                    <div className="space-y-2">
                      {assets.map((asset) => (
                        <button
                          key={asset.id}
                          className="btn btn-outline btn-block justify-start text-left"
                          onClick={() => handleAssetClick(asset)}
                        >
                          <div>
                            <div className="font-semibold">{asset.name || asset.label}</div>
                            {asset.status && (
                              <div className="text-xs text-base-content/70">Status: {asset.status}</div>
                            )}
                          </div>
                        </button>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>
        )}
      </main>
    </div>
  );
}
