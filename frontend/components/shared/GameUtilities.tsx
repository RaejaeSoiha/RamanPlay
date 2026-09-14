"use client";

import { useEffect, useState } from "react";
import { Bell, CalendarPlus, Clock3, Radio } from "lucide-react";

import type { Game } from "../../types";

type LiveDetails = {
  status_detail: string;
  period: number | null;
  clock: string;
  possession: string;
  down_distance: string;
  last_play: string;
};

function calendarText(game: Game) {
  if (!game.kickoff_time) return "";
  const start = new Date(game.kickoff_time);
  const end = new Date(start.getTime() + 3 * 60 * 60 * 1000);
  const stamp = (date: Date) => date.toISOString().replace(/[-:]/g, "").replace(/\.\d{3}Z$/, "Z");
  const title = `${game.away_team.city} ${game.away_team.name} at ${game.home_team.city} ${game.home_team.name}`;
  return [
    "BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//RamanPlay//EN", "BEGIN:VEVENT",
    `UID:ramanplay-game-${game.id}@local`, `DTSTAMP:${stamp(new Date())}`,
    `DTSTART:${stamp(start)}`, `DTEND:${stamp(end)}`, `SUMMARY:${title}`,
    `LOCATION:${game.venue || "See provider"}`, "END:VEVENT", "END:VCALENDAR",
  ].join("\r\n");
}

export default function GameUtilities({ game }: { game: Game }) {
  const [details, setDetails] = useState<LiveDetails | null>(null);
  const [reminder, setReminder] = useState("30");
  const [reminderMessage, setReminderMessage] = useState("");
  const isLive = ["LIVE", "HALFTIME"].includes(game.status);

  useEffect(() => {
    if (!isLive) return;
    let active = true;
    fetch(`/api/games/${game.id}/live-details`)
      .then((response) => response.ok ? response.json() : null)
      .then((data) => { if (active && data) setDetails(data); })
      .catch(() => {});
    return () => { active = false; };
  }, [game.id, isLive]);

  const downloadCalendar = () => {
    const content = calendarText(game);
    if (!content) return;
    const blob = new Blob([content], { type: "text/calendar;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = `ramanplay-${game.id}.ics`;
    anchor.click();
    URL.revokeObjectURL(url);
  };

  const scheduleReminder = async () => {
    if (!game.kickoff_time) return;
    if (!("Notification" in window)) {
      setReminderMessage("Browser notifications are not supported on this device.");
      return;
    }
    const permission = Notification.permission === "default" ? await Notification.requestPermission() : Notification.permission;
    if (permission !== "granted") {
      setReminderMessage("Allow notifications in your browser to receive this reminder.");
      return;
    }
    const minutes = Number(reminder);
    const delay = new Date(game.kickoff_time).getTime() - Date.now() - minutes * 60_000;
    if (delay <= 0) {
      setReminderMessage("This reminder time has already passed.");
      return;
    }
    const title = `${game.away_team.name} at ${game.home_team.name}`;
    window.setTimeout(() => new Notification(title, { body: `Starts in ${minutes} minutes.`, tag: `ramanplay-${game.id}` }), delay);
    setReminderMessage(`Reminder set for ${minutes} minutes before kickoff while RamanPlay is open.`);
  };

  return <div className="game-utilities">
    {isLive && details && (details.status_detail || details.clock || details.last_play) && <section className="live-score-details" aria-label="Live score details">
      <div><Radio size={16} /><strong>Live game details</strong></div>
      <span>{details.status_detail || `${details.period ? `Period ${details.period}` : "Live"}${details.clock ? ` · ${details.clock}` : ""}`}</span>
      {details.possession && <span>Possession: {details.possession}</span>}
      {details.down_distance && <span>{details.down_distance}</span>}
      {details.last_play && <p>{details.last_play}</p>}
    </section>}
    <section className="game-planner" aria-label="Game planning tools">
      <div><CalendarPlus size={19} /><div><strong>Plan this game</strong><span>Add it to your calendar or set a browser reminder.</span></div></div>
      <button className="secondary-button" type="button" disabled={!game.kickoff_time} onClick={downloadCalendar}>Add to calendar</button>
      <label><Clock3 size={16} /><span className="sr-only">Reminder time</span><select value={reminder} onChange={(event) => setReminder(event.target.value)}><option value="15">15 min</option><option value="30">30 min</option><option value="60">1 hour</option></select></label>
      <button className="secondary-button" type="button" disabled={!game.kickoff_time} onClick={scheduleReminder}><Bell size={15} /> Remind me</button>
      {reminderMessage && <p>{reminderMessage}</p>}
    </section>
  </div>;
}
