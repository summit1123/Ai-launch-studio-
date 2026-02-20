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
  autoPlay?: boolean;
  disabled?: boolean;
};

export function VoicePlaybackToggle({
  sessionId,
  text,
  autoPlay = false,
  disabled = false,
}: VoicePlaybackToggleProps) {
  const [loading, setLoading] = useState(false);
  const [playing, setPlaying] = useState(false);
  const [audioUrl, setAudioUrl] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const lastAutoplayKeyRef = useRef<string | null>(null);

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

  useEffect(() => {
    if (!sessionId || !text.trim() || !autoPlay || disabled || loading || playing) {
      return;
    }

    const key = `${sessionId}:${text.trim()}`;
    if (lastAutoplayKeyRef.current === key) {
      return;
    }

    void (async () => {
      const success = await playFromText({ forceNewAudio: true });
      if (success) {
        lastAutoplayKeyRef.current = key;
      }
    })();
  }, [autoPlay, disabled, loading, playing, sessionId, text]);

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

  const playFromText = async ({
    forceNewAudio = false,
  }: {
    forceNewAudio?: boolean;
  }): Promise<boolean> => {
    if (!sessionId || !text.trim() || disabled || loading) {
      return false;
    }
    setError(null);
    let targetUrl = forceNewAudio ? null : audioUrl;

    try {
      setLoading(true);
      if (!targetUrl) {
        const response = await createAssistantVoice(sessionId, {
          text,
          voice_preset: "cute_ko",
          format: "mp3",
        });
        targetUrl = resolveAudioUrl(response.audio_url);
        setAudioUrl(targetUrl);
      }

      await startPlayback(targetUrl);
      return true;
    } catch (playError) {
      const message =
        playError instanceof Error
          ? playError.message
          : "어시스턴트 음성 생성에 실패했습니다.";
      setError(message);
      setPlaying(false);
      return false;
    } finally {
      setLoading(false);
    }
  };

  const handleToggle = async () => {
    if (!sessionId || !text.trim() || disabled || loading) {
      return;
    }

    if (playing) {
      stopPlayback();
      return;
    }

    await playFromText({ forceNewAudio: false });
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
