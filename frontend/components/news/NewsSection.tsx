"use client";

import { useEffect, useState } from "react";
import { ArrowUpRight, Newspaper } from "lucide-react";

import { newsEndpoint, relativeNewsTime, storySportClass, type NewsSport } from "../../lib/news";
import type { NewsStory } from "../../types";

function NewsCard({ story }: { story: NewsStory }) {
  const published = new Date(story.published_at);
  return (
    <a className="news-card" href={story.source_url} target="_blank" rel="noopener noreferrer" aria-label={`Read ${story.headline} from ${story.source_name}`}>
      {story.image_url ? <img className="news-card-image" src={story.image_url} alt="" /> : <span className="news-card-image news-card-image-fallback" aria-hidden="true"><Newspaper size={24} /></span>}
      <span className="news-card-body">
        <span className="news-card-meta">
          <span className={`news-sport-badge ${storySportClass(story)}`}>{story.league}</span>
          <span>{story.source_name}</span>
          <time dateTime={story.published_at} title={published.toLocaleString()}>{relativeNewsTime(story.published_at)}</time>
        </span>
        <strong>{story.headline}</strong>
        {story.description ? <span className="news-card-description">{story.description}</span> : null}
        <span className="news-card-read">Read story <ArrowUpRight size={15} aria-hidden="true" /></span>
      </span>
    </a>
  );
}

export default function NewsSection({ sport = "ALL", limit = 6 }: { sport?: NewsSport; limit?: number }) {
  const [stories, setStories] = useState<NewsStory[]>([]);
  const [state, setState] = useState<"loading" | "ready" | "empty" | "error">("loading");

  useEffect(() => {
    let active = true;
    setState("loading");
    fetch(newsEndpoint(sport, limit))
      .then(async (response) => {
        if (!response.ok) throw Error("Sports news is currently unavailable.");
        return response.json() as Promise<NewsStory[]>;
      })
      .then((rows) => {
        if (!active) return;
        setStories(rows);
        setState(rows.length ? "ready" : "empty");
      })
      .catch(() => active && setState("error"));
    return () => { active = false; };
  }, [sport, limit]);

  const title = sport === "ALL" ? "Top stories" : `${sport} stories`;
  return (
    <section className="news-section" aria-labelledby={`news-section-${sport.toLowerCase()}`}>
      <div className="section-heading"><h2 id={`news-section-${sport.toLowerCase()}`}>{title}</h2><span>Headlines from ESPN</span></div>
      {state === "loading" ? (
        <div className="news-grid news-skeletons" aria-label="Loading sports news">{Array.from({ length: Math.min(limit, 4) }, (_, index) => <span className="news-skeleton" key={index} />)}</div>
      ) : state === "ready" ? (
        <div className="news-grid">{stories.map((story) => <NewsCard key={story.id} story={story} />)}</div>
      ) : state === "empty" ? (
        <div className="empty compact">No {sport === "ALL" ? "sports" : sport} stories are available right now.</div>
      ) : (
        <div className="notice news-unavailable"><Newspaper size={21} /><span>Sports news is temporarily unavailable. Scores and schedules are still available.</span></div>
      )}
    </section>
  );
}
