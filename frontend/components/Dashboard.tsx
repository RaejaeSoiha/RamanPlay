"use client";
import { useState, useEffect, useCallback, useRef } from "react";
import Link from "next/link";
import Maintenance from "./Maintenance";
import MyLinks from "./MyLinks";
import AccountFeatures from "./AccountFeatures";
import Standings from "./Standings";
import { Badge, Crest } from "./ui";
import {
  ArrowUpRight,
  ArrowLeft,
  Search,
  Star,
  CalendarDays,
  Radio,
  Settings,
  House,
  ShieldCheck,
  ChevronRight,
  RefreshCw,
  SlidersHorizontal,
  Headphones,
  ExternalLink,
  Menu,
  X,
  Check,
  MonitorPlay,
  LockKeyhole,
  Play,
  PlayCircle,
  CreditCard,
  Trophy,
} from "lucide-react";
import type { Game, Team, Source, Preferences, Subscription } from "../types";
import {
  kickoff,
  gameDate,
  toggleFavorite,
  favoriteFirst,
  teamColors,
  showScores,
  seasonLabel,
} from "../lib/helpers";
import { showWatchLive } from "../lib/myLinks";
const defaults: Preferences = {
  timezone: "America/Denver",
  autoRefresh: true,
  showPaid: true,
  showFree: true,
  showAudio: true,
  league: "ALL",
};
const nav = [
  ["Home", House],
  ["Today", Radio],
  ["Schedule", CalendarDays],
  ["Standings", Trophy],
  ["Teams", ShieldCheck],
  ["Favorites", Star],
  ["Subscriptions", CreditCard],
  ["Settings", Settings],
] as const;
export default function Dashboard({ gameId }: { gameId?: string }) {
  const [view, setView] = useState("Home"),
    [period, setPeriod] = useState("all"),
    [games, setGames] = useState<Game[]>([]),
    [teams, setTeams] = useState<Team[]>([]),
    [detail, setDetail] = useState<Game | null>(null),
    [favorites, setFavorites] = useState<number[]>([]),
    [prefs, setPrefs] = useState(defaults),
    [ready, setReady] = useState(false),
    [query, setQuery] = useState(""),
    [debounced, setDebounced] = useState(""),
    [error, setError] = useState(""),
    [loading, setLoading] = useState(true),
    [filters, setFilters] = useState(false),
    [mobile, setMobile] = useState(false),
    [access, setAccess] = useState(""),
    [team, setTeam] = useState(""),
    [conference, setConference] = useState(""),
    [division, setDivision] = useState(""),
    [network, setNetwork] = useState(""),
    [status, setStatus] = useState(""),
    [date, setDate] = useState(""),
    [lastUpdated, setLastUpdated] = useState(""),
    [demo, setDemo] = useState(false),
    [refreshSeconds, setRefreshSeconds] = useState(120),
    [providerState, setProviderState] = useState("");
  const [subscriptions, setSubscriptions] = useState<Subscription[]>([]);
  useEffect(() => {
    try {
      setFavorites(JSON.parse(localStorage.getItem("nwf-favorites") || "[]"));
      setPrefs({
        ...defaults,
        timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
        ...JSON.parse(localStorage.getItem("nwf-settings") || "{}"),
      });
    } catch {}
    const initialView = new URLSearchParams(window.location.search).get("view");
    if (initialView && nav.some(([name]) => name === initialView)) {
      setView(initialView);
      setPeriod(initialView === "Today" ? "today" : "all");
    }
    const initialTeam = new URLSearchParams(window.location.search).get("team");
    if (initialTeam) setTeam(initialTeam);
    const initialLeague = new URLSearchParams(window.location.search).get("league");
    if (initialLeague && ["ALL", "NFL", "NBA"].includes(initialLeague.toUpperCase())) {
      setPrefs((current) => ({ ...current, league: initialLeague.toUpperCase() as Preferences["league"] }));
    }
    setReady(true);
    loadSubscriptions();
  }, []);
  const requestVersion = useRef(0);
  const loadSubscriptions = useCallback(async () => {
    try {
      const response = await fetch("/api/subscriptions");
      if (response.ok) {
        const data = await response.json();
        setSubscriptions(data);
      }
    } catch {}
  }, []);

  useEffect(() => {
    loadSubscriptions();
  }, [loadSubscriptions]);

  useEffect(() => {
    if (ready) {
      localStorage.setItem("nwf-favorites", JSON.stringify(favorites));
      localStorage.setItem("nwf-settings", JSON.stringify(prefs));
    }
  }, [favorites, prefs, ready]);
  useEffect(() => {
    const t = setTimeout(() => setDebounced(query), 250);
    return () => clearTimeout(t);
  }, [query]);

  const load = useCallback(async () => {
    const version = ++requestVersion.current;
    try {
      const params = new URLSearchParams({
        q: debounced,
        period,
        tz: prefs.timezone,
        access,
        team,
        conference,
        division,
        network,
        status,
        date,
        league: prefs.league,
      });
      const response = await fetch(
        gameId ? "/api/games/" + gameId : "/api/games?" + params,
      );
      if (!response.ok)
        throw Error("Unable to load games. Check that the backend is running.");
      const data = await response.json();
      const healthResponse = await fetch("/api/health");
      if (healthResponse.ok) {
        const health = await healthResponse.json();
        if (gameId && data.development_data && !health.development_data) {
          window.location.replace("/");
          return;
        }
        if (version === requestVersion.current) {
          setDemo(health.development_data);
          setRefreshSeconds(Math.max(60, health.refresh_seconds));
          setProviderState(health.provider_status);
        }
      }
      if (version !== requestVersion.current) return;
      if (gameId) setDetail(data);
      else setGames(data);
      setError("");
      setLastUpdated(
        new Date().toLocaleTimeString([], {
          hour: "numeric",
          minute: "2-digit",
        }),
      );
    } catch (e) {
      if (version === requestVersion.current) setError((e as Error).message);
    } finally {
      if (version === requestVersion.current) setLoading(false);
    }
  }, [
    gameId,
    debounced,
    period,
    prefs.timezone,
    access,
    team,
    conference,
    division,
    network,
    status,
    date,
    prefs.league,
  ]);
  useEffect(() => {
    if (ready) load();
  }, [load, ready]);
  useEffect(() => {
    if (!prefs.autoRefresh || !ready) return;
    const timer = setInterval(load, refreshSeconds * 1000);
    return () => clearInterval(timer);
  }, [load, prefs.autoRefresh, ready, refreshSeconds]);
  useEffect(() => {
    fetch("/api/teams")
      .then((r) => {
        if (!r.ok) throw Error();
        return r.json();
      })
      .then(setTeams)
      .catch(() => {});
  }, []);
  const updateSubscription = async (
    providerName: string,
    changes: { has_subscription?: boolean; has_free_trial?: boolean },
  ) => {
    try {
      await fetch(`/api/subscriptions/${providerName}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(changes),
      });
      setSubscriptions((prev) =>
        prev.map((s) =>
          s.provider_name === providerName
            ? { ...s, ...changes, updated_at: new Date().toISOString() }
            : s,
        ),
      );
    } catch {}
  };
  function go(v: string) {
    setView(v);
    setMobile(false);
    setPeriod(v === "Today" ? "today" : "all");
    setAccess("");
    setStatus("");
    setTeam("");
    setConference("");
    setDivision("");
    setNetwork("");
    setDate("");
    setQuery("");
  }
  const displayed = favoriteFirst(games, favorites).filter(
    (g) =>
      view !== "Favorites" ||
      favorites.includes(g.away_team.id) ||
      favorites.includes(g.home_team.id),
  );
  const live = displayed.filter((g) => ["LIVE", "HALFTIME"].includes(g.status));
  const next = displayed.filter((g) =>
    ["SCHEDULED", "PRE_GAME"].includes(g.status),
  );
  const free = displayed.filter((g) =>
    g.sources.some(
      (s) => s.is_free && !["ERROR", "BLOCKED", "NOT_FOUND"].includes(s.status),
    ),
  );
  const visibleSources = (sources: Source[]) =>
    sources.filter(
      (s) =>
        (prefs.showPaid ||
          !["SUBSCRIPTION", "FREE TRIAL"].includes(s.access_type)) &&
        (prefs.showFree || s.access_type !== "FREE") &&
        (prefs.showAudio || s.access_type !== "AUDIO ONLY"),
    );
  function card(g: Game) {
    const active = ["LIVE", "HALFTIME"].includes(g.status);
    return (
      <article
        className={"game-card " + (active ? "active-game" : "")}
        key={g.id}
      >
        <div className="card-top">
          <span className={active ? "live-label" : "muted"}>
            {active ? (
              <>
                <i /> {g.status === "HALFTIME" ? "HALFTIME" : "LIVE NOW"}
              </>
            ) : g.status === "FINAL" ? (
              "FINAL"
            ) : (
              kickoff(g.kickoff_time, prefs.timezone)
            )}
          </span>
          <span className="network">
            <Badge>{g.league}</Badge> {g.broadcast_network || "Network unknown"}
          </span>
        </div>
        <Link
          href={"/game/" + g.id}
          className="matchup"
          aria-label={g.away_team.name + " at " + g.home_team.name}
        >
          {active && (
            <span className="live-play-overlay" title="Game is live">
              <PlayCircle size={32} />
            </span>
          )}
          <div>
            <Crest team={g.away_team} />
            <span className="city">{g.away_team.city}</span>
            <strong>{g.away_team.name}</strong>
          </div>
          <span className={"versus " + (active ? "score" : "")}>
            {showScores(g) ? (
              <>
                {g.away_score}
                <span>:</span>
                {g.home_score}
              </>
            ) : (
              "vs"
            )}
          </span>
          <div>
            <Crest team={g.home_team} />
            <span className="city">{g.home_team.city}</span>
            <strong>{g.home_team.name}</strong>
          </div>
        </Link>
        <div className="card-meta">
          <span>
            {gameDate(g.kickoff_time, prefs.timezone)}
            <br />
            {seasonLabel(g)}
          </span>
          <button
            className={
              "icon-button " +
              (favorites.includes(g.away_team.id) ? "selected" : "")
            }
            onClick={() =>
              setFavorites(toggleFavorite(favorites, g.away_team.id))
            }
            aria-label={"Favorite " + g.away_team.name}
          >
            <Star
              size={17}
              fill={
                favorites.includes(g.away_team.id) ? "currentColor" : "none"
              }
            />
          </button>
        </div>
        <div className="card-bottom">
          <Badge kind={g.my_links.some((link) => link.enabled) ? "free" : "official"}>
            <ShieldCheck size={12} />{" "}
            {g.my_links.some((link) => link.enabled)
              ? "MY LINK READY"
              : g.sources.some((s) => s.is_free)
              ? "FREE OPTION"
              : g.sources.some((s) => s.access_type === "SUBSCRIPTION")
                ? "SUBSCRIPTION"
                : g.sources.length
                  ? "OFFICIAL GUIDE"
                  : "WATCH OPTIONS"}
          </Badge>
          {showWatchLive(g) && (
            <Link className="card-live-watch" href={`/game/${g.id}?watch=best`}>
              <Play size={13} /> WATCH LIVE
            </Link>
          )}
          <Link href={"/game/" + g.id}>
            Watch options <ArrowUpRight size={16} />
          </Link>
        </div>
      </article>
    );
  }
  return (
    <div className="app-shell">
      <aside className={"sidebar " + (mobile ? "open" : "")}>
        <Link href="/" className="brand">
          <span className="brand-mark">
            R<span>P</span>
          </span>
          <span>
            RamanPlay<span className="brand-sub">All Your Games. One Place.</span>
          </span>
        </Link>
        <div className="nav-caption">YOUR GAMES</div>
        <nav>
          {nav.map(([label, Icon]) => (
            <a
              key={label}
              href={"/?view=" + label}
              className={
                view === label && !gameId ? "nav-item current" : "nav-item"
              }
              onClick={(e) => {
                if (!gameId && !e.metaKey && !e.ctrlKey) {
                  e.preventDefault();
                  go(label);
                }
              }}
              tabIndex={0}
            >
              <Icon size={19} />
              {label}
              {label === "Favorites" && favorites.length > 0 && (
                <span className="count">{favorites.length}</span>
              )}
            </a>
          ))}
        </nav>
        <div className="sidebar-teams">
          <div className="nav-caption">
            MY TEAMS <Star size={12} />
          </div>
          {teams
            .filter((t) => favorites.includes(t.id))
            .map((t) => (
              <button
                key={t.id}
                onClick={() => {
                  if (gameId) {
                    window.location.href =
                      "/?view=Schedule&team=" + t.abbreviation;
                    return;
                  }
                  go("Schedule");
                  setTeam(t.abbreviation);
                }}
              >
                <Crest small team={t} />
                {t.city} {t.name}
              </button>
            ))}
          {favorites.length === 0 && (
            <p>
              Keep your teams close.
              <br />
              Tap a star to follow them.
            </p>
          )}
        </div>
        <div className="sidebar-bottom">
          <ShieldCheck size={20} />
          <div>
            Official sources + your links
            <small>Your game-day watch list.</small>
          </div>
        </div>
      </aside>
      <div className="main-shell">
        <header className="topbar">
          <button
            className="icon-button mobile-menu"
            onClick={() => setMobile(!mobile)}
            aria-label="Toggle navigation"
          >
            {mobile ? <X /> : <Menu />}
          </button>
          <span className="breadcrumb">
            {detail?.league || (prefs.league === "ALL" ? "Games" : prefs.league)} <ChevronRight size={13} /> {gameId ? "Game center" : view}
          </span>
          <div className="topbar-right">
            {!gameId && (
              <div className="tabs league-tabs" aria-label="League selector">
                {(["ALL", "NFL", "NBA"] as const).map((value) => (
                  <button
                    className={prefs.league === value ? "active" : ""}
                    key={value}
                    onClick={() => {
                      setPrefs({ ...prefs, league: value });
                      setTeam("");
                      setConference("");
                      setDivision("");
                    }}
                  >
                    {value === "ALL" ? "All" : value}
                  </button>
                ))}
              </div>
            )}
            <span className="timezone">
              {prefs.timezone.replaceAll("_", " ").split("/").pop()} time
            </span>
            <span className="avatar">ME</span>
          </div>
        </header>
        <main>
          {(demo ||
            detail?.development_data ||
            games.some((g) => g.development_data)) && (
            <div className="demo-banner">
              <span>DEVELOPMENT DATA</span> Sample or trial data. Not a verified
              live schedule.
            </div>
          )}
          {providerState === "Error" && (
            <div className="notice" role="status">
              The schedule provider could not update. Showing the last available
              data. See Settings → Maintenance for details.
            </div>
          )}
          {error && (
            <div className="error" role="alert">
              {error} <button onClick={load}>Try again</button>
            </div>
          )}
          {gameId ? (
            <>
              <Link className="back-link" href="/">
                <ArrowLeft size={16} /> Back to games
              </Link>
              {detail && (
                <>
                  <div className="page-heading">
                    <div>
                      <div className="eyebrow">
                        {detail.league} · {seasonLabel(detail)} · GAME CENTER
                      </div>
                      <h1>
                        {detail.away_team.abbreviation}{" "}
                        <span className="muted">at</span>{" "}
                        {detail.home_team.abbreviation}
                      </h1>
                    </div>
                    <Badge>{detail.status.replace("_", " ")}</Badge>
                  </div>
                  <section className="detail-match">
                    <div>
                      <Crest team={detail.away_team} />
                      <h2>
                        {detail.away_team.city}
                        <br />
                        {detail.away_team.name}
                      </h2>
                      {detail.away_record && <p className="muted">{detail.away_record}</p>}
                      <button
                        className="text-button"
                        onClick={() =>
                          setFavorites(
                            toggleFavorite(favorites, detail.away_team.id),
                          )
                        }
                      >
                        <Star size={16} />
                        {favorites.includes(detail.away_team.id)
                          ? "Following"
                          : "Follow team"}
                      </button>
                    </div>
                    <div className="match-center">
                      <div className="detail-score">
                        {showScores(detail)
                          ? `${detail.away_score} : ${detail.home_score}`
                          : "VS"}
                      </div>
                      <strong>
                        {gameDate(detail.kickoff_time, prefs.timezone)}
                      </strong>
                      <p>{kickoff(detail.kickoff_time, prefs.timezone)}</p>
                      <Badge>
                        {detail.broadcast_network || "Network unknown"}
                      </Badge>
                      {detail.venue && <p className="muted">{detail.venue}</p>}
                    </div>
                    <div>
                      <Crest team={detail.home_team} />
                      <h2>
                        {detail.home_team.city}
                        <br />
                        {detail.home_team.name}
                      </h2>
                      {detail.home_record && <p className="muted">{detail.home_record}</p>}
                      <button
                        className="text-button"
                        onClick={() =>
                          setFavorites(
                            toggleFavorite(favorites, detail.home_team.id),
                          )
                        }
                      >
                        <Star size={16} />
                        {favorites.includes(detail.home_team.id)
                          ? "Following"
                          : "Follow team"}
                      </button>
                    </div>
                  </section>
                  <MyLinks
                    gameId={detail.id}
                    links={detail.my_links || []}
                    officialSources={detail.sources}
                    live={detail.status === "LIVE"}
                  />
                  <div className="section-heading">
                    <h2>Official watch options</h2>
                    <span>Free options first</span>
                  </div>
                  <p className="muted">
                    Availability depends on your location, device, and provider.
                    A reachable link does not verify game playback.
                  </p>
<div className="source-list">
                      {visibleSources(detail.sources).map((s) => (
                        <article className="source" key={s.id}>
                          <span className="source-icon">
                            {s.access_type === "AUDIO ONLY" ? (
                              <Headphones />
                            ) : s.game_status === "LIVE" ? (
                              <PlayCircle className="live-play" size={28} />
                            ) : (
                              <MonitorPlay />
                            )}
                          </span>
                          <div className="source-copy">
                            <div className="source-title">
                              <h3>{s.source_name}</h3>
                              <Badge kind={s.is_free ? "free" : "official"}>
                                {s.access_type}
                              </Badge>
                              {s.user_has_subscription && (
                                <Badge kind="sub">YOURS</Badge>
                              )}
                              {s.user_has_free_trial && !s.user_has_subscription && (
                                <Badge kind="trial">FREE TRIAL</Badge>
                              )}
                              {s.game_status === "LIVE" && (
                                <Badge kind="live">LIVE NOW</Badge>
                              )}
                              {["NOT_FOUND", "BLOCKED", "ERROR"].includes(
                                s.status,
                              ) && <Badge>UNAVAILABLE</Badge>}
                              {s.is_official && <ShieldCheck size={16} />}
                            </div>
                            <p>{s.notes}</p>
                            <small>
                              {s.provider_name} · {s.region} · {s.status}{" "}
                              {s.last_checked &&
                                " · Checked " +
                                  new Date(s.last_checked).toLocaleString()}
                            </small>
                          </div>
                          <a
                            className="primary-button"
                            href={(s.game_status === "LIVE" && s.live_url) ? s.live_url : s.url}
                            target="_blank"
                            rel="noopener noreferrer"
                          >
                            {s.access_type === "AUDIO ONLY"
                              ? "LISTEN"
                              : s.access_type === "OFFICIAL"
                              ? "WATCH GUIDE"
                              : s.game_status === "LIVE"
                              ? <>
                                  <Play size={14} /> WATCH LIVE
                                </>
                              : "WATCH"}
                            <ArrowUpRight size={16} />
                          </a>
                        </article>
                      ))}
                    </div>
                  {visibleSources(detail.sources).length === 0 && (
                    <div className="empty">
                      No sources match your display settings.
                    </div>
                  )}
                  <div className="notice">
                    <ShieldCheck />
                    Official guides help you find coverage. Only options
                    explicitly labeled FREE provide verified free video access.
                  </div>
                </>
              )}
              {loading && <div className="empty">Loading game…</div>}
            </>
          ) : view === "Settings" ? (
            <>
              <div className="page-heading">
                <div className="eyebrow">MAKE IT YOURS</div>
                <h1>Settings</h1>
              </div>
              <section className="settings-panel">
                <h2>Viewing preferences</h2>
                <label>
                  Kickoff time zone
                  <select
                    value={prefs.timezone}
                    onChange={(e) =>
                      setPrefs({ ...prefs, timezone: e.target.value })
                    }
                  >
                    {Array.from(
                      new Set([
                        Intl.DateTimeFormat().resolvedOptions().timeZone,
                        "America/New_York",
                        "America/Chicago",
                        "America/Denver",
                        "America/Los_Angeles",
                        prefs.timezone,
                      ]),
                    ).map((t) => (
                      <option key={t}>{t}</option>
                    ))}
                  </select>
                </label>
                {(
                  [
                    ["autoRefresh", "Refresh games every 2 minutes"],
                    ["showPaid", "Show subscription and trial sources"],
                    ["showFree", "Show free sources"],
                    ["showAudio", "Show audio coverage"],
                  ] as const
                ).map(([k, label]) => (
                  <label key={k}>
                    {label}
                    <input
                      type="checkbox"
                      checked={prefs[k]}
                      onChange={(e) =>
                        setPrefs({ ...prefs, [k]: e.target.checked })
                      }
                    />
                  </label>
                ))}
                <p className="muted">
                  Preferences and favorite teams are saved on this browser.
                  Notifications are disabled.
                </p>
                <button className="text-button" onClick={() => go("Teams")}>
                  Manage favorite teams <ChevronRight size={16} />
                </button>
                <p className="muted">
                  Link-check frequency can be changed in Maintenance below. The
                  default is set with LINK_CHECK_HOURS (default: 6 hours).
                </p>
              </section>
              <section className="settings-panel">
                <h2>My Subscriptions</h2>
                <p className="muted">
                  Mark services you pay for or have free trials. Your sources
                  appear first and show badges.
                </p>
                {subscriptions.length === 0 ? (
                  <p className="muted">Loading…</p>
                ) : (
                  <div className="subscriptions-grid">
                    {subscriptions.map((sub) => (
                      <label key={sub.id} className="subscription-row">
                        <div className="sub-info">
                          <strong>{sub.source_name}</strong>
                          <small>{sub.provider_name}</small>
                        </div>
                        <div className="sub-toggles">
                          <span>
                            <input
                              type="checkbox"
                              checked={sub.has_subscription}
                              onChange={(e) =>
                                updateSubscription(sub.provider_name, {
                                  has_subscription: e.target.checked,
                                })
                              }
                            />
                            Subscribed
                          </span>
                          <span>
                            <input
                              type="checkbox"
                              checked={sub.has_free_trial}
                              onChange={(e) =>
                                updateSubscription(sub.provider_name, {
                                  has_free_trial: e.target.checked,
                                })
                              }
                            />
                            Free Trial
                          </span>
                        </div>
                      </label>
                    ))}
                  </div>
                )}
              </section>
              <Maintenance />
              <AccountFeatures />
            </>
          ) : view === "Standings" ? (
            <Standings league={prefs.league} />
          ) : view === "Teams" ? (
            <>
              <div className="page-heading">
                <div>
                  <div className="eyebrow">ALL {prefs.league === "ALL" ? "TEAMS" : prefs.league + " TEAMS"}. YOUR FAVORITES FIRST.</div>
                  <h1>Find your team.</h1>
                </div>
              </div>
              <div className="teams-grid">
                {teams.filter((t) => prefs.league === "ALL" || t.league === prefs.league).sort(
                    (a, b) =>
                      Number(favorites.includes(b.id)) -
                      Number(favorites.includes(a.id)),
                  )
                  .map((t) => (
                    <article className="team-tile" key={t.id}>
                      <Crest team={t} />
                      <div>
                        <small>
                          {t.league} · {t.conference} {t.division}
                        </small>
                        <h3>
                          {t.city}
                          <br />
                          {t.name}
                        </h3>
                      </div>
                      <button
                        className={
                          "icon-button " +
                          (favorites.includes(t.id) ? "selected" : "")
                        }
                        aria-label={"Favorite " + t.name}
                        onClick={() =>
                          setFavorites(toggleFavorite(favorites, t.id))
                        }
                      >
                        <Star
                          fill={
                            favorites.includes(t.id) ? "currentColor" : "none"
                          }
                        />
                      </button>
                    </article>
                  ))}
              </div>
            </>
          ) : (
            <>
              <div className="page-heading">
                <div>
                  <div className="eyebrow">YOUR SEAT. EVERY GAME.</div>
                  <h1>
                    {view === "Favorites"
                      ? "Your teams. Your games."
                      : view === "Today"
                        ? "Today’s game plan."
                        : view === "Schedule"
                          ? "The full game plan."
                          : "Games start here."}
                  </h1>
                  <p>Find your game. See your options. Don’t miss a moment.</p>
                </div>
                <button className="secondary-button" onClick={load}>
                  <RefreshCw size={15} /> Refresh games
                </button>
              </div>
              <div className="summary-strip">
                <div>
                  <Radio size={19} />
                  <strong>{live.length}</strong>
                  <span>live {demo ? "samples" : "games"}</span>
                </div>
                <div>
                  <CalendarDays size={19} />
                  <strong>{next.length}</strong>
                  <span>upcoming</span>
                </div>
                <div>
                  <ShieldCheck size={19} />
                  <strong>{free.length}</strong>
                  <span>verified free options</span>
                </div>
                <div className="updated">Updated {lastUpdated || "—"}</div>
              </div>
              <div className="search-row">
                <div className="search-box">
                  <Search size={19} />
                  <input
                    aria-label="Search games"
                    placeholder="Search teams, matchups, or “Sunday games”"
                    value={query}
                    onChange={(e) => setQuery(e.target.value)}
                  />
                  {query && (
                    <button
                      className="icon-button"
                      aria-label="Clear search"
                      onClick={() => setQuery("")}
                    >
                      <X size={16} />
                    </button>
                  )}
                </div>
                <button
                  className={"secondary-button " + (filters ? "selected" : "")}
                  onClick={() => setFilters(!filters)}
                >
                  <SlidersHorizontal size={17} /> Filters
                </button>
              </div>
              <div className="filter-row">
                <div className="tabs">
                  {(["ALL", "NFL", "NBA"] as const).map((value) => (
                    <button
                      className={prefs.league === value ? "active" : ""}
                      key={value}
                      onClick={() => {
                        setPrefs({ ...prefs, league: value });
                        setTeam("");
                        setConference("");
                        setDivision("");
                      }}
                    >
                      {value === "ALL" ? "All" : value}
                    </button>
                  ))}
                </div>
                <div className="tabs">
                  {[
                    ["all", "All games"],
                    ["today", "Today"],
                    ["tomorrow", "Tomorrow"],
                    ["week", "This week"],
                    ["weekend", "This weekend"],
                  ].map(([key, label]) => (
                    <button
                      className={period === key ? "active" : ""}
                      key={key}
                      onClick={() => setPeriod(key)}
                    >
                      {label}
                    </button>
                  ))}
                </div>
                <button
                  className={"free-toggle " + (access === "FREE" ? "on" : "")}
                  onClick={() => setAccess(access === "FREE" ? "" : "FREE")}
                >
                  <span className="toggle-track">
                    <span />
                  </span>{" "}
                  Free only
                </button>
              </div>
              {filters && (
                <div className="advanced-filters">
                  <label>
                    Team
                    <select
                      value={team}
                      onChange={(e) => setTeam(e.target.value)}
                    >
                      <option value="">All teams</option>
                      {teams.filter((t) => prefs.league === "ALL" || t.league === prefs.league).map((t) => (
                        <option key={t.id} value={t.abbreviation}>
                          {t.city} {t.name}
                        </option>
                      ))}
                    </select>
                  </label>
                  <label>
                    Conference
                    <select
                      value={conference}
                      onChange={(e) => setConference(e.target.value)}
                    >
                      <option value="">All</option>
                      {[...new Set(teams.filter((t) => prefs.league === "ALL" || t.league === prefs.league).map((t) => t.conference))].sort().map((name) => <option key={name}>{name}</option>)}
                    </select>
                  </label>
                  <label>
                    Division
                    <select
                      value={division}
                      onChange={(e) => setDivision(e.target.value)}
                    >
                      <option value="">All</option>
                      {[...new Set(teams.filter((t) => prefs.league === "ALL" || t.league === prefs.league).map((t) => t.division))].sort().map((x) => (
                        <option key={x}>{x}</option>
                      ))}
                    </select>
                  </label>
                  <label>
                    Network
                    <select
                      value={network}
                      onChange={(e) => setNetwork(e.target.value)}
                    >
                      <option value="">All</option>
                      {[
                        "NBC",
                        "CBS",
                        "FOX",
                        "ESPN",
                        "ABC",
                        "Prime Video",
                        "NFL Network",
                        "Netflix",
                      ].map((x) => (
                        <option key={x}>{x}</option>
                      ))}
                    </select>
                  </label>
                  <label>
                    Status
                    <select
                      value={status}
                      onChange={(e) => setStatus(e.target.value)}
                    >
                      <option value="">All</option>
                      {[
                        "LIVE",
                        "UPCOMING",
                        "FINAL",
                        "POSTPONED",
                        "CANCELLED",
                      ].map((x) => (
                        <option key={x}>{x}</option>
                      ))}
                    </select>
                  </label>
                  <label>
                    Access
                    <select
                      value={access}
                      onChange={(e) => setAccess(e.target.value)}
                    >
                      <option value="">All</option>
                      {[
                        "FREE",
                        "OFFICIAL",
                        "FREE TRIAL",
                        "SUBSCRIPTION",
                        "AUDIO ONLY",
                      ].map((x) => (
                        <option key={x}>{x}</option>
                      ))}
                    </select>
                  </label>
                  <label>
                    Date
                    <input
                      type="date"
                      value={date}
                      onChange={(e) => setDate(e.target.value)}
                    />
                  </label>
                  <button
                    className="text-button"
                    onClick={() => {
                      setTeam("");
                      setConference("");
                      setDivision("");
                      setNetwork("");
                      setStatus("");
                      setDate("");
                      setAccess("");
                    }}
                  >
                    Reset filters
                  </button>
                </div>
              )}
              {loading ? (
                <div className="empty">Loading your game plan…</div>
              ) : displayed.length === 0 ? (
                <div className="empty">
                  <Search size={30} />
                  <h2>
                    {access === "FREE"
                      ? "No verified free streams found."
                      : "No games found."}
                  </h2>
                  <p>
                    {access === "FREE"
                      ? "Free coverage will appear here only when the schedule feed provides a confirmed legal option."
                      : "Try another date or team, or update the schedule in Settings."}
                  </p>
                </div>
              ) : (
                <>
                  {view === "Home" &&
                  !debounced &&
                  !filters &&
                  period === "all" ? (
                    <>
                      <div className="dashboard-columns">
                        <div>
                          <div className="section-heading">
                            <h2>
                              <span className="live-dot" /> Live now
                            </h2>
                            <span>
                              {live.length}{" "}
                              {live.length === 1 ? "game" : "games"}
                            </span>
                          </div>
                          {live.length ? (
                            <div className="game-grid live-grid">
                              {live.map(card)}
                            </div>
                          ) : (
                            <div className="empty compact">
                              No games are live right now.
                            </div>
                          )}
                        </div>
                        <aside className="coverage-note">
                          <span className="eyebrow">
                            THE RIGHT WAY TO WATCH
                          </span>
                          <ShieldCheck size={32} />
                          <h2>
                            Less searching.
                            <br />
                            More games.
                          </h2>
                          <p>
                            Official links. Clear access labels.
                            <br />
                            No questionable streams.
                          </p>
                          <button
                            onClick={() => {
                              go("Schedule");
                              setAccess("OFFICIAL");
                            }}
                          >
                            Explore official options <ArrowUpRight size={16} />
                          </button>
                        </aside>
                      </div>
                      <div className="section-heading">
                        <h2>
                          Up next{" "}
                          <span className="section-count">{next.length}</span>
                        </h2>
                        <button
                          className="text-button"
                          onClick={() => go("Schedule")}
                        >
                          Full schedule <ArrowUpRight size={15} />
                        </button>
                      </div>
                      <div className="game-grid">
                        {next.slice(0, 6).map(card)}
                      </div>
                      <div className="section-heading">
                        <h2>Free options</h2>
                        <Badge kind="free">VERIFIED ONLY</Badge>
                      </div>
                      {free.length ? (
                        <div className="game-grid">{free.map(card)}</div>
                      ) : (
                        <div className="notice">
                          <ShieldCheck size={22} />
                          <div>
                            <strong>
                              No verified free video options in this schedule.
                            </strong>
                            <p>
                              Check each game’s official guide for current
                              availability in your area.
                            </p>
                          </div>
                        </div>
                      )}
                    </>
                  ) : (
                    <>
                      <div className="section-heading">
                        <h2>
                          {view === "Favorites" ? "Following" : "Game schedule"}{" "}
                          <span className="section-count">
                            {displayed.length}
                          </span>
                        </h2>
                        <span>Kickoff in your selected time zone</span>
                      </div>
                      <div className="game-grid">{displayed.map(card)}</div>
                    </>
                  )}
                </>
              )}
            </>
          )}
          <footer>
            <span className="footer-brand">RAMANPLAY</span>
            <span>All Your Games. One Place.</span>
            <span>
              <ShieldCheck size={13} /> Legal sources. Always.
            </span>
          </footer>
        </main>
      </div>
    </div>
  );
}
