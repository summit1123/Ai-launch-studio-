import { useEffect, useRef, useState } from "react";

import { createAssistantVoice } from "../api/client";

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8090/api";

function resolveAudioUrl(pathOrUrl: string): string {
  if (pathOrUrl.startsWith("http://") || pathOrUrl.startsWith("https://")) {
    return pathOrUrl;
  }
  const backendBase = API_BASE_URL.endsWith("/api")
    ? API_BASE_URL.slice(0, -4)
    : API_BASE_URL;
  if (pathOrUrl.startsWith("/")) {
    return `${backendBase}${pathOrUrl}`;
  }
  return `${backendBase}/${pathOrUrl}`;
}

type VoicePlaybackToggleProps = {
  sessionId: string | null;
  text: string;
  disabled?: boolean;
};

export function VoicePlaybackToggle({
  sessionId,
  text,
  disabled = false,
}: VoicePlaybackToggleProps) {
  const [loading, setLoading] = useState(false);
  const [playing, setPlaying] = useState(false);
  const [audioUrl, setAudioUrl] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const audioRef = useRef<HTMLAudioElement | null>(null);

  useEffect(() => {
    return () => {
      audioRef.current?.pause();
      audioRef.current = null;
    };
  }, []);

  useEffect(() => {
    stopPlayback();
    setAudioUrl(null);
    setError(null);
    // text/session이 바뀌면 이전 질문 음성을 버린다.
  }, [sessionId, text]);

  const stopPlayback = () => {
    const audio = audioRef.current;
    if (!audio) {
      return;
    }
    audio.pause();
    audio.currentTime = 0;
    setPlaying(false);
  };

  const startPlayback = async (url: string) => {
    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current = null;
    }
    audioRef.current = new Audio(url);
    audioRef.current.onended = () => setPlaying(false);
    await audioRef.current.play();
    setPlaying(true);
  };

  const handleToggle = async () => {
    if (!sessionId || !text.trim() || disabled || loading) {
      return;
    }

    if (playing) {
      stopPlayback();
      return;
    }

    setError(null);
    let targetUrl = audioUrl;

    try {
      setLoading(true);
      if (!targetUrl) {
        const response = await createAssistantVoice(sessionId, {
          text,
          voice_preset: "friendly_ko",
          format: "mp3",
        });
        targetUrl = resolveAudioUrl(response.audio_url);
        setAudioUrl(targetUrl);
      }

      await startPlayback(targetUrl);
    } catch (playError) {
      const message =
        playError instanceof Error
          ? playError.message
          : "어시스턴트 음성 생성에 실패했습니다.";
      setError(message);
      setPlaying(false);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ display: "grid", gap: "6px" }}>
      <button
        type="button"
        className="btn-secondary-sm"
        disabled={disabled || loading || !sessionId || !text.trim()}
        onClick={handleToggle}
      >
        {loading
          ? "질문 음성 생성 중..."
          : playing
            ? "질문 음성 정지"
            : audioUrl
              ? "질문 음성 다시 재생"
              : "질문 음성 듣기"}
      </button>
      {error && <small style={{ color: "#fda4af" }}>{error}</small>}
    </div>
  );
}
