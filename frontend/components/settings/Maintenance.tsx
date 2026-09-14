"use client";
import { useState } from "react";
import { LockKeyhole } from "lucide-react";
import { Badge } from "../shared/SportUI";
export default function Maintenance() {
  const [key, setKey] = useState(""),
    [stats, setStats] = useState<Record<string, string | number> | null>(null),
    [message, setMessage] = useState(""),
    [busy, setBusy] = useState(false),
    [hours, setHours] = useState(6);
  async function action(path: string, method = "GET") {
    setBusy(true);
    setMessage("");
    try {
      const r = await fetch("/api/admin/" + path, {
        method,
        headers: {
          Authorization: "Bearer " + key,
          "Content-Type": "application/json",
        },
        ...(path === "settings" ? { body: JSON.stringify({ hours }) } : {}),
      });
      const data = await r.json();
      if (!r.ok) throw Error(data.detail || "Request failed");
      if (path === "status") {
        setStats(data);
        setHours(Number(data.link_check_hours || 6));
      } else {
        setMessage(
          path === "settings"
            ? "Link-check schedule saved."
            : path === "check-links"
              ? `Checked ${data.checked ?? 0} source records. ${data.status || ""}`
              : data.errors
                ? data.error
                : `Games fetched: ${data.fetched}. Created: ${data.games_created}. Updated: ${data.games_updated}. Errors: 0.`,
        );
        const statusResponse = await fetch("/api/admin/status", {
          headers: { Authorization: "Bearer " + key },
        });
        if (statusResponse.ok) setStats(await statusResponse.json());
      }
    } catch (e) {
      setMessage((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <section className="settings-panel maintenance">
      <div className="section-heading">
        <h2>
          <LockKeyhole size={19} /> Maintenance
        </h2>
        <Badge>PROTECTED</Badge>
      </div>
      <p className="muted">
        Use the ADMIN_SECRET from your backend environment. Your key stays in
        memory for this page only.
      </p>
      <label>
        Maintenance key
        <input
          type="password"
          autoComplete="off"
          value={key}
          onChange={(e) => setKey(e.target.value)}
          placeholder="Enter your maintenance key"
        />
      </label>
      <button
        className="secondary-button"
        disabled={busy || !key}
        onClick={() => action("status")}
      >
        Unlock status
      </button>
      {stats && (
        <>
          <div className="stats-grid">
            {Object.entries(stats).map(([k, v]) => (
              <div key={k}>
                <small>{k.replaceAll("_", " ")}</small>
                <strong>{String(v) || "—"}</strong>
              </div>
            ))}
          </div>
          <label className="frequency-setting">
            Check links every (hours)
            <input
              type="number"
              min="1"
              max="168"
              value={hours}
              onChange={(e) => setHours(Number(e.target.value))}
            />
            <button
              className="secondary-button"
              disabled={busy || hours < 1 || hours > 168}
              onClick={() => action("settings", "POST")}
            >
              Save frequency
            </button>
          </label>
          <div className="maintenance-actions">
            {["update-schedule", "check-links", "rebuild-sources"].map((a) => (
              <button
                className="secondary-button"
                key={a}
                disabled={busy}
                onClick={() => action(a, "POST")}
              >
                {a.replaceAll("-", " ")}
              </button>
            ))}
          </div>
        </>
      )}
      {busy && (
        <p role="status">Working… Link checks can take a few minutes.</p>
      )}
      {message && <p role="status">{message}</p>}
    </section>
  );
}
