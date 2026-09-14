"use client";

import { useEffect, useRef, useState } from "react";
import { ExternalLink, Maximize, Minimize2, PictureInPicture2, Radio, X } from "lucide-react";
import type { DirectMediaKind } from "../../lib/playback";

type InlineVideoPlayerProps = {
  sourceUrl: string;
  sourceType: DirectMediaKind;
  title: string;
  poster?: string;
  isLive?: boolean;
  onClose: () => void;
  onOpenWatchOptions?: () => void;
};

export default function InlineVideoPlayer({
  sourceUrl,
  sourceType,
  title,
  poster,
  isLive = false,
  onClose,
  onOpenWatchOptions,
}: InlineVideoPlayerProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const videoRef = useRef<HTMLVideoElement>(null);
  const [needsUnmute, setNeedsUnmute] = useState(false);
  const [needsPlay, setNeedsPlay] = useState(false);
  const [failed, setFailed] = useState(false);
  const [fullscreen, setFullscreen] = useState(false);
  const [canPictureInPicture, setCanPictureInPicture] = useState(false);
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    const video = videoRef.current;
    if (!video) return;
    let disposed = false;
    let hls: { destroy: () => void } | null = null;

    async function startWithSound() {
      video.muted = false;
      try {
        await video.play();
        setNeedsUnmute(false);
        setNeedsPlay(false);
      } catch {
        // Some browsers allow autoplay only after muting. Keep the player clean and
        // let the viewer explicitly restore sound with the visible player control.
        video.muted = true;
        try {
          await video.play();
          setNeedsUnmute(true);
          setNeedsPlay(false);
        } catch {
          setNeedsUnmute(false);
          setNeedsPlay(true);
        }
      }
    }

    async function start() {
      setFailed(false);
      setNeedsUnmute(false);
      setNeedsPlay(false);
      const playWhenReady = () => void startWithSound();
      if (sourceType === "hls" && !video.canPlayType("application/vnd.apple.mpegurl")) {
        const { default: Hls } = await import("hls.js");
        if (disposed) return;
        if (!Hls.isSupported()) {
          setFailed(true);
          return;
        }
        const player = new Hls();
        hls = player;
        player.attachMedia(video);
        player.on(Hls.Events.MEDIA_ATTACHED, () => player.loadSource(sourceUrl));
        player.on(Hls.Events.MANIFEST_PARSED, playWhenReady);
        player.on(Hls.Events.ERROR, (_, data) => {
          if (data.fatal) setFailed(true);
        });
      } else {
        video.src = sourceUrl;
        video.load();
        playWhenReady();
      }
    }
    void start();
    return () => {
      disposed = true;
      hls?.destroy();
    };
  }, [attempt, sourceType, sourceUrl]);

  useEffect(() => {
    setCanPictureInPicture(Boolean(document.pictureInPictureEnabled && videoRef.current?.requestPictureInPicture));
    const updateFullscreen = () => setFullscreen(document.fullscreenElement === containerRef.current);
    document.addEventListener("fullscreenchange", updateFullscreen);
    return () => document.removeEventListener("fullscreenchange", updateFullscreen);
  }, []);

  async function toggleFullscreen() {
    const container = containerRef.current;
    const video = videoRef.current as (HTMLVideoElement & { webkitEnterFullscreen?: () => void }) | null;
    if (!container || !video) return;
    try {
      if (document.fullscreenElement) await document.exitFullscreen();
      else if (container.requestFullscreen) await container.requestFullscreen();
      else video.webkitEnterFullscreen?.();
    } catch {
      // The browser can reject fullscreen outside a user gesture.
    }
  }

  async function openPictureInPicture() {
    try {
      if (videoRef.current && document.pictureInPictureEnabled) {
        await videoRef.current.requestPictureInPicture();
      }
    } catch {
      // The native browser control remains available when Picture-in-Picture is denied.
    }
  }

  function retry() {
    setFailed(false);
    setNeedsUnmute(false);
    setNeedsPlay(false);
    setAttempt((current) => current + 1);
  }

  function enableSound() {
    const video = videoRef.current;
    if (!video) return;
    video.muted = false;
    void video.play().then(
      () => {
        setNeedsUnmute(false);
        setNeedsPlay(false);
      },
      () => setNeedsPlay(true),
    );
  }

  return (
    <section className="inline-video-player" ref={containerRef} aria-label={`${title} inline player`}>
      {failed ? (
        <div className="inline-video-failure">
          <strong>Stream unavailable.</strong>
          <span>The stream may be unavailable, expired, or unsupported by this browser.</span>
          <div className="inline-video-failure-actions">
            <button className="secondary-button" onClick={retry}>Retry</button>
            {onOpenWatchOptions && <button className="secondary-button" onClick={onOpenWatchOptions}>Open another watch option <ExternalLink size={15} /></button>}
          </div>
        </div>
      ) : (
        <>
          <video
            ref={videoRef}
            className="inline-video"
            controls
            autoPlay
            playsInline
            preload="metadata"
            poster={poster}
            onError={() => setFailed(true)}
            onVolumeChange={(event) => {
              if (!event.currentTarget.muted) setNeedsUnmute(false);
            }}
            aria-label={title}
          />
          {needsUnmute && <button className="inline-video-notice" onClick={enableSound}>Tap to unmute</button>}
          {needsPlay && <button className="inline-video-notice" onClick={enableSound}>Tap to play with sound</button>}
        </>
      )}
      <div className="inline-video-toolbar">
        {isLive && <span className="inline-video-live"><Radio size={13} /> LIVE</span>}
        <span className="inline-video-title">{title}</span>
        {canPictureInPicture && !failed && <button className="icon-button" aria-label="Picture in Picture" title="Picture in Picture" onClick={() => void openPictureInPicture()}><PictureInPicture2 size={17} /></button>}
        {!failed && <button className="icon-button" aria-label={fullscreen ? "Exit full screen" : "Full screen"} title={fullscreen ? "Exit full screen" : "Full screen"} onClick={() => void toggleFullscreen()}>{fullscreen ? <Minimize2 size={17} /> : <Maximize size={17} />}</button>}
        <button className="text-button inline-video-close" onClick={onClose}><X size={16} /> Close player</button>
      </div>
    </section>
  );
}
