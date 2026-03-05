import { useEffect, useRef, useState } from "react";
import { Html5Qrcode } from "html5-qrcode";
import { getCachedAHU } from "../../offline/ahuCache";

/**
 * Extract the asset_id from a scanned QR code text.
 *
 * Handles three formats:
 *  1. New universal format: "https://app.com/scan?asset_id=42"  → "42"
 *  2. Legacy FilterInfo URL: "https://app.com/FilterInfo/42"    → "42"
 *  3. Plain value: "42" or "AHU-001"                            → as-is
 */
function extractAssetId(decodedText) {
  const s = (decodedText || "").trim();

  if (!s.includes("http")) {
    // Plain label or numeric id
    return s;
  }

  try {
    const u = new URL(s);

    // New format: /scan?asset_id=<id>
    const assetId = u.searchParams.get("asset_id");
    if (assetId) return assetId;

    // Legacy format: /FilterInfo/<id>
    const parts = u.pathname.split("/").filter(Boolean);
    return parts[parts.length - 1] || s;
  } catch {
    return s;
  }
}

/**
 * Determine where to navigate after a successful scan.
 *
 * - If the QR encodes a `?asset_id=` URL  → use the new /asset-scan route
 * - Otherwise (legacy plain label / FilterInfo URL) → use the old /FilterInfo route
 */
function resolveNavigationTarget(decodedText, assetId) {
  if (decodedText.includes("asset_id=") || /^\d+$/.test(assetId)) {
    // Numeric IDs go to the new universal scan page
    return `/asset-scan?asset_id=${encodeURIComponent(assetId)}`;
  }
  // Legacy label → legacy FilterInfo page
  return `/FilterInfo/${encodeURIComponent(assetId)}`;
}

export default function QRScanner() {
  const scannerRef = useRef(null);
  const [status, setStatus] = useState("Initializing camera…");
  const [error, setError] = useState(null);
  const [offline, setOffline] = useState(!navigator.onLine);
  const [scanned, setScanned] = useState(false);

  // Online / Offline detection
  useEffect(() => {
    const handleOnline = () => setOffline(false);
    const handleOffline = () => setOffline(true);
    window.addEventListener("online", handleOnline);
    window.addEventListener("offline", handleOffline);
    return () => {
      window.removeEventListener("online", handleOnline);
      window.removeEventListener("offline", handleOffline);
    };
  }, []);

  // Start QR scanner
  useEffect(() => {
    const scanner = new Html5Qrcode("qr-reader");
    scannerRef.current = scanner;

    setStatus(offline ? "Offline mode: scanning from downloads…" : "Starting camera…");

    scanner
      .start(
        { facingMode: "environment" },
        { fps: 10, qrbox: { width: 250, height: 250 } },
        async (decodedText) => {
          if (scanned) return;
          setScanned(true);
          setStatus("QR detected ✓");

          const assetId = extractAssetId(decodedText);

          try {
            await scanner.stop();
          } catch (_) {}

          try {
            if (!assetId) {
              setError("Invalid QR code");
              setStatus("Scan error");
              setScanned(false);
              return;
            }

            // Require login before proceeding
            const tech = localStorage.getItem("tech");
            if (!tech) {
              const target = resolveNavigationTarget(decodedText, assetId);
              try {
                sessionStorage.setItem("post_login_path", target);
              } catch (_) {}
              window.location.assign("/");
              return;
            }

            // Offline: check cache
            if (!navigator.onLine) {
              setStatus("Checking offline downloads…");
              const cached = await getCachedAHU(assetId);
              if (cached) {
                setStatus("Opening cached asset…");
                window.location.assign(resolveNavigationTarget(decodedText, assetId));
              } else {
                setStatus("Not downloaded for offline use.");
                window.location.assign(`/offline-not-downloaded/${encodeURIComponent(assetId)}`);
              }
              return;
            }

            // Online: navigate
            setStatus("Opening asset…");
            window.location.assign(resolveNavigationTarget(decodedText, assetId));
          } catch (e) {
            console.error(e);
            setError("Failed to open scanned asset");
            setStatus("Scan error");
          }
        }
      )
      .then(() => setStatus("Point camera at QR code"))
      .catch((err) => {
        console.error(err);
        setError("Camera access failed");
        setStatus("Camera error");
      });

    return () => {
      scanner.stop().catch(() => {});
    };
  }, [offline, scanned]);

  return (
    <div className="min-h-screen bg-base-200 flex items-center justify-center p-4">
      <div className="w-full max-w-md bg-base-100 rounded-xl shadow-lg p-4 space-y-4">
        <h1 className="text-xl font-bold text-primary text-center">
          Scan QR Code
        </h1>

        {offline && (
          <div className="rounded-lg bg-warning/20 border border-warning px-3 py-2 text-sm text-warning">
            📶 You are offline. Scanning only works for downloaded assets.
          </div>
        )}

        {error && (
          <div className="rounded-lg bg-error/20 border border-error px-3 py-2 text-sm text-error">
            ❌ {error}
          </div>
        )}

        <div className="relative rounded-lg overflow-hidden border border-base-300">
          <div id="qr-reader" className="w-full" />
          <div className="absolute inset-0 pointer-events-none flex items-center justify-center">
            <div className="w-56 h-56 border-2 border-primary rounded-lg" />
          </div>
        </div>

        <div className="text-center text-sm text-base-content/70">{status}</div>

        {error && (
          <button
            onClick={() => window.location.reload()}
            className="btn btn-primary btn-sm w-full"
          >
            Retry
          </button>
        )}
      </div>
    </div>
  );
}
