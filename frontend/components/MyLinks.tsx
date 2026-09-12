"use client";

import { useEffect, useRef, useState } from "react";
import {
  CheckCircle2,
  ExternalLink,
  Link2,
  Pencil,
  Plus,
  Power,
  RefreshCw,
  Trash2,
  XCircle,
  Copy,
  TriangleAlert,
} from "lucide-react";
import type { MyLink } from "../types";
import { bestMyLink, cleanOpenAction, sortMyLinks } from "../lib/myLinks";

type LinkForm = {
  url: string;
  source_name: string;
  notes: string;
  priority: number;
  enabled: boolean;
  shared_with_household: boolean;
};

const emptyForm: LinkForm = {
  url: "",
  source_name: "",
  notes: "",
  priority: 3,
  enabled: true,
  shared_with_household: false,
};

function toForm(link: MyLink): LinkForm {
  return {
    url: link.url,
    source_name: link.source_name,
    notes: link.notes,
    priority: link.priority,
    enabled: link.enabled,
    shared_with_household: link.shared_with_household,
  };
}

function domainOf(url: string | null) {
  if (!url) return null;
  try {
    return new URL(url).hostname;
  } catch {
    return null;
  }
}

type OfficialSource = {
  provider_name: string;
  source_name: string;
  url: string;
  access_type: string;
};

export default function MyLinks({
  gameId,
  links,
  officialSources = [],
  live = false,
}: {
  gameId: number;
  links: MyLink[];
  officialSources?: OfficialSource[];
  live?: boolean;
}) {
  const [items, setItems] = useState(links);
  const [form, setForm] = useState<LinkForm | null>(null);
  const [editing, setEditing] = useState<number | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [hideDisabledOrWarning, setHideDisabledOrWarning] = useState(false);
  const [opening, setOpening] = useState<number | null>(null);
  const [copied, setCopied] = useState<number | null>(null);
  const [csrfToken, setCsrfToken] = useState("");
  const [roomCode, setRoomCode] = useState("");
  const mediaRef = useRef<HTMLVideoElement>(null);
  const autoOpenStarted = useRef(false);

  useEffect(() => {
    setHideDisabledOrWarning(
      window.localStorage.getItem("my-links-hide-disabled-or-warning") === "true",
    );
  }, []);
  useEffect(() => {
    fetch("/api/account/me")
      .then((response) => response.json())
      .then((account) => setCsrfToken(account.csrf_token || ""))
      .catch(() => {});
  }, []);

  const ordered = sortMyLinks(items);
  const best = bestMyLink(items);
  const visibleItems = ordered.filter(
    (link) =>
      !hideDisabledOrWarning || (link.enabled && link.status !== "WARNING"),
  );

  function setHiddenLinks(value: boolean) {
    setHideDisabledOrWarning(value);
    window.localStorage.setItem("my-links-hide-disabled-or-warning", String(value));
  }

  async function copyLink(link: MyLink) {
    try {
      await navigator.clipboard.writeText(link.url);
      setCopied(link.id);
      window.setTimeout(() => setCopied(null), 1500);
    } catch {
      setError("Unable to copy this link.");
    }
  }

  async function request(path: string, options?: RequestInit) {
    const response = await fetch(path, {
      ...options,
      headers: { "Content-Type": "application/json", ...options?.headers },
    });
    if (!response.ok) {
      const data = await response.json().catch(() => null);
      throw Error(data?.detail || "Unable to save this link.");
    }
    return response.status === 204 ? null : response.json();
  }

  async function save(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!form) return;
    setBusy(true);
    setError("");
    try {
      const result = await request(
        editing === null ? `/api/my-links/${gameId}` : `/api/my-links/${editing}`,
        {
          method: editing === null ? "POST" : "PATCH",
          body: JSON.stringify(form),
        },
      );
      setItems((current) =>
        editing === null
          ? [...current, result]
          : current.map((item) => (item.id === result.id ? result : item)),
      );
      setForm(null);
      setEditing(null);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  async function update(id: number, data: Partial<LinkForm>) {
    setBusy(true);
    setError("");
    try {
      const result = await request(`/api/my-links/${id}`, {
        method: "PATCH",
        body: JSON.stringify(data),
      });
      setItems((current) =>
        current.map((item) => (item.id === result.id ? result : item)),
      );
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  async function refresh(id: number) {
    setBusy(true);
    setError("");
    try {
      const result = await request(`/api/my-links/${id}/check`, { method: "POST" });
      setItems((current) =>
        current.map((item) => (item.id === result.id ? result : item)),
      );
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  async function remove(id: number) {
    setBusy(true);
    setError("");
    try {
      await request(`/api/my-links/${id}`, { method: "DELETE" });
      setItems((current) => current.filter((item) => item.id !== id));
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  async function navigate(link: MyLink) {
    if (!link.final_url) return;
    setBusy(true);
    setError("");
    try {
      const result = await request(`/api/my-links/${link.id}/opened`, {
        method: "POST",
      });
      setItems((current) =>
        current.map((item) => (item.id === result.id ? { ...item, ...result } : item)),
      );
      window.location.assign(link.final_url);
    } catch (err) {
      setError((err as Error).message);
      setBusy(false);
    }
  }

  function openLink(link: MyLink | null) {
    const action = cleanOpenAction(link);
    if (!link || action === "blocked") {
      setError("This link is blocked or has no safe, resolved destination. Choose another My Link.");
      return;
    }
    if (action === "confirm") {
      setOpening(link.id);
      return;
    }
    void navigate(link);
  }

  async function createWatchRoom() {
    if (!best || !csrfToken) return;
    const response = await fetch("/api/watch-together", {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-CSRF-Token": csrfToken },
      body: JSON.stringify({ game_id: gameId, selected_link_id: best.id }),
    });
    if (!response.ok) {
      setError("Only the household owner can create a Watch Together room.");
      return;
    }
    setRoomCode((await response.json()).code);
  }

  function watchOnTv(link: MyLink) {
    const remote = mediaRef.current?.remote;
    if (remote) {
      void remote.prompt().catch(() => setError("No cast device is available. Playing on this device instead."));
    } else {
      void mediaRef.current?.play().catch(() => setError("TV playback is unavailable for this source."));
    }
  }

  useEffect(() => {
    if (
      autoOpenStarted.current ||
      new URLSearchParams(window.location.search).get("watch") !== "best"
    ) return;
    autoOpenStarted.current = true;
    openLink(best);
  }, [best]);

  return (
    <section className="my-links">
      <div className="section-heading">
        <div>
          <h2>My Links</h2>
          <span>Personal links appear before official watch sources.</span>
        </div>
        <div className="my-links-controls">
          <label className="my-links-filter">
            <input
              type="checkbox"
              checked={hideDisabledOrWarning}
              onChange={(event) => setHiddenLinks(event.target.checked)}
            />
            Hide disabled or warning links
          </label>
          {best && (
            <button
              className={live ? "primary-button my-link-live-button" : "secondary-button"}
              disabled={busy}
              onClick={() => openLink(best)}
            >
              {live ? "▶ WATCH LIVE" : "Open Best Link"}
              <ExternalLink size={16} />
            </button>
          )}
          {officialSources.length > 0 && (
            <select
              className="official-source-select"
              defaultValue="-1"
              onChange={(e) => {
                const idx = Number(e.target.value);
                if (idx >= 0) {
                  const src = officialSources[idx];
                  setForm({
                    url: src.url,
                    source_name: `${src.provider_name} - ${src.source_name}`,
                    notes: `Added from official sources: ${src.access_type}`,
                    priority: 2,
                    enabled: true,
                    shared_with_household: false,
                  });
                  setEditing(null);
                  setError("");
                  e.target.value = "-1";
                }
              }}
            >
              <option value="-1" disabled>
                + Add from official source…
              </option>
              {officialSources.map((src, i) => (
                <option key={i} value={i}>
                  {src.provider_name} — {src.source_name} ({src.access_type})
                </option>
              ))}
            </select>
          )}
          <button
            className="secondary-button"
            onClick={() => {
              setForm(emptyForm);
              setEditing(null);
              setError("");
            }}
            disabled={busy}
          >
            <Plus size={16} /> Add link
          </button>
        </div>
      </div>
      {error && <div className="error my-links-error" role="alert">{error}</div>}
      {form && (
        <form className="my-link-form" onSubmit={save}>
          <label>
            URL
            <input
              required
              type="url"
              value={form.url}
              onChange={(event) => setForm({ ...form, url: event.target.value })}
              placeholder="https://…"
            />
          </label>
          <label>
            Source name
            <input
              required
              value={form.source_name}
              onChange={(event) =>
                setForm({ ...form, source_name: event.target.value })
              }
              placeholder="My provider"
            />
          </label>
          <label>
            Priority
            <select
              value={form.priority}
              onChange={(event) =>
                setForm({ ...form, priority: Number(event.target.value) })
              }
            >
              {[1, 2, 3, 4, 5].map((priority) => (
                <option key={priority} value={priority}>
                  {priority}
                </option>
              ))}
            </select>
          </label>
          <label className="my-link-notes">
            Notes
            <textarea
              value={form.notes}
              onChange={(event) => setForm({ ...form, notes: event.target.value })}
              placeholder="Optional notes"
            />
          </label>
          <label className="my-link-enabled">
            <input
              type="checkbox"
              checked={form.enabled}
              onChange={(event) => setForm({ ...form, enabled: event.target.checked })}
            />
            Enable this link
          </label>
          <label className="my-link-enabled">
            <input
              type="checkbox"
              checked={form.shared_with_household}
              onChange={(event) => setForm({ ...form, shared_with_household: event.target.checked })}
            />
            Share with household
          </label>
          <p>Links are checked only on approved public HTTPS domains.</p>
          <div className="my-link-form-actions">
            <button className="primary-button" disabled={busy}>
              {busy ? "Checking…" : editing === null ? "Save link" : "Save changes"}
            </button>
            <button
              type="button"
              className="text-button"
              onClick={() => {
                setForm(null);
                setEditing(null);
              }}
            >
              Cancel
            </button>
          </div>
        </form>
      )}
      <div className="source-list">
        {visibleItems.map((link) => (
          <article className="source my-link" key={link.id}>
            <span className="source-icon"><Link2 /></span>
            <div className="source-copy">
              <div className="source-title">
                <h3>{link.source_name}</h3>
                {(link.is_best || best?.id === link.id) && (
                  <span className="my-link-best">BEST LINK</span>
                )}
                <span className={`my-link-status ${link.status.toLowerCase()}`}>
                  {link.status === "ONLINE" || link.status === "REDIRECT" ? (
                    <CheckCircle2 size={14} />
                  ) : link.status === "WARNING" ? (
                    <TriangleAlert size={14} />
                  ) : (
                    <XCircle size={14} />
                  )}
                  {link.status}
                </span>
                {!link.enabled && <span className="my-link-disabled">DISABLED</span>}
                <span className="my-link-sharing">{link.shared_with_household ? "HOUSEHOLD" : "PRIVATE"}</span>
              </div>
              {link.notes && <p>{link.notes}</p>}
              <small>
                Priority {link.priority}
                {link.last_checked && ` · Checked ${new Date(link.last_checked).toLocaleString()}`}
              </small>
              <small className="my-link-reliability">
                Reliability {link.reliability_score}% · {link.successful_check_count} successful · {link.failure_count} failed
                {link.average_response_time > 0 && ` · ${link.average_response_time.toFixed(1)}s avg`}
                {link.redirect_count > 0 && ` · ${link.redirect_count} redirect${link.redirect_count === 1 ? "" : "s"}`}
                {link.last_opened_at && ` · Last opened ${new Date(link.last_opened_at).toLocaleString()}`}
              </small>
              {link.final_url && (
                <small className="my-link-destination">
                  Resolved destination: {link.final_destination_domain || domainOf(link.final_url)}
                </small>
              )}
              {link.status === "WARNING" && (
                <small className="my-link-warning">
                  Unexpected redirect behavior detected. Review the destination before opening.
                </small>
              )}
              {opening === link.id && (
                <div className="my-link-open-confirmation">
                  {link.final_url && domainOf(link.final_url) ? (
                    <>
                      <span>Opens in this tab: <strong>{link.final_destination_domain || domainOf(link.final_url)}</strong></span>
                      <button
                        className="secondary-button"
                        onClick={() => {
                          setOpening(null);
                          void navigate(link);
                        }}
                      >
                        Confirm open <ExternalLink size={15} />
                      </button>
                    </>
                  ) : (
                    <span>Check this link before opening it. Its final destination could not be safely resolved.</span>
                  )}
                  <button className="text-button" onClick={() => setOpening(null)}>Cancel</button>
                </div>
              )}
            </div>
            <div className="my-link-actions">
              <button
                className="primary-button"
                disabled={!link.enabled || !["ONLINE", "REDIRECT", "WARNING"].includes(link.status) || !link.final_url || busy}
                title={link.status === "BLOCKED" ? "This link is blocked" : !link.final_url ? "Check this link to resolve its destination" : undefined}
                onClick={() => openLink(link)}
              >
                Open Link <ExternalLink size={16} />
              </button>
              <button className="secondary-button" onClick={() => copyLink(link)}>
                <Copy size={16} /> {copied === link.id ? "Copied" : "Copy Link"}
              </button>
              <button className="icon-button" title="Check link" aria-label="Check link" disabled={busy || !link.enabled} onClick={() => refresh(link.id)}>
                <RefreshCw size={16} />
              </button>
              <button className="my-link-toggle" disabled={busy} onClick={() => update(link.id, { enabled: !link.enabled })}>
                <Power size={15} /> {link.enabled ? "Disable" : "Enable"}
              </button>
              <button className="icon-button" title="Edit link" aria-label="Edit link" disabled={busy} onClick={() => { setForm(toForm(link)); setEditing(link.id); setError(""); }}>
                <Pencil size={16} />
              </button>
              <button className="icon-button destructive" title="Delete link" aria-label="Delete link" disabled={busy} onClick={() => remove(link.id)}>
                <Trash2 size={16} />
              </button>
            </div>
            {live && link.final_url && /\.(m3u8|mpd)(?:$|[?#])/i.test(link.final_url) && (
              <div className="my-link-tv">
                <video ref={mediaRef} controls src={link.final_url} />
                <button className="secondary-button" onClick={() => watchOnTv(link)}>Watch on TV</button>
              </div>
            )}
          </article>
        ))}
      </div>
      {live && best && (
        <div className="watch-together">
          <button className="secondary-button" onClick={createWatchRoom}>Watch Together</button>
          {roomCode && <span>Invite code: <strong>{roomCode}</strong></span>}
        </div>
      )}
      {items.length === 0 && <div className="empty compact">No personal links saved for this game.</div>}
    </section>
  );
}
