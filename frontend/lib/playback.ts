import type { MyLink } from "../types";

export type PlaybackSourceType = MyLink["playback_type"];
export type DirectMediaKind = "hls" | "dash" | "file";

export function directMediaKind(url: string): DirectMediaKind | null {
  let pathname: string;
  try {
    pathname = new URL(url).pathname.toLowerCase();
  } catch {
    return null;
  }
  if (pathname.endsWith(".m3u8")) return "hls";
  if (pathname.endsWith(".mpd")) return "dash";
  if (/\.(mp4|webm|ogv|ogg)$/.test(pathname)) return "file";
  return null;
}

export function playbackSourceType(link: MyLink | null): PlaybackSourceType {
  if (!link || !link.enabled || link.status === "BLOCKED") return "BLOCKED";
  if (
    link.playback_type === "DIRECT_MEDIA" &&
    ["ONLINE", "REDIRECT"].includes(link.status) &&
    link.final_url &&
    directMediaKind(link.final_url)
  ) {
    return "DIRECT_MEDIA";
  }
  // Only a checked direct-media URL may reach the native player. Every other
  // source stays on the external-navigation path, including legacy embeds.
  return "EXTERNAL_PAGE";
}

export function directPlayableUrl(link: MyLink | null): string | null {
  return playbackSourceType(link) === "DIRECT_MEDIA" ? link?.final_url || null : null;
}

export function directPlayableKind(link: MyLink | null): DirectMediaKind | null {
  const url = directPlayableUrl(link);
  return url ? directMediaKind(url) : null;
}
