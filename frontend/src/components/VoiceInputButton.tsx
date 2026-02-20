import { useRef, useState, type ChangeEvent } from "react";

import type { VoiceTurnRequest } from "../types";

type VoiceInputButtonProps = {
  disabled?: boolean;
  loading?: boolean;
  onSubmit: (payload: VoiceTurnRequest) => Promise<void>;
};

export function VoiceInputButton({
  disabled = false,
  loading = false,
  onSubmit,
}: VoiceInputButtonProps) {
  const [recording, setRecording] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const recorderRef = useRef<MediaRecorder | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const chunksRef = useRef<Blob[]>([]);

  const canRecord =
    typeof window !== "undefined" &&
    typeof navigator !== "undefined" &&
    Boolean(navigator.mediaDevices?.getUserMedia) &&
    typeof MediaRecorder !== "undefined";

  const openFilePicker = () => {
    fileInputRef.current?.click();
  };

  const stopTracks = () => {
    streamRef.current?.getTracks().forEach((track) => track.stop());
    streamRef.current = null;
  };

  const handleFileChange = async (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    event.currentTarget.value = "";
    if (!file || disabled || loading) {
      return;
    }
    setError(null);
    await onSubmit({
      audio: file,
      filename: file.name,
      locale: "ko-KR",
      voice_preset: "cute_ko",
    });
  };

  const startRecording = async () => {
    if (!canRecord || disabled || loading || recording) {
      return;
    }
    setError(null);
    chunksRef.current = [];

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const recorder = new MediaRecorder(stream, {
        mimeType: MediaRecorder.isTypeSupported("audio/webm")
          ? "audio/webm"
          : undefined,
      });

      streamRef.current = stream;
      recorderRef.current = recorder;

      recorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          chunksRef.current.push(event.data);
        }
      };

      recorder.onstop = async () => {
        try {
          const blob = new Blob(chunksRef.current, {
            type: recorder.mimeType || "audio/webm",
          });
          chunksRef.current = [];
          if (blob.size > 0) {
            await onSubmit({
              audio: blob,
              filename: `voice_${Date.now()}.webm`,
              locale: "ko-KR",
              voice_preset: "cute_ko",
            });
          }
        } finally {
          stopTracks();
          recorderRef.current = null;
        }
      };

      recorder.start();
      setRecording(true);
    } catch (recordError) {
      const message =
        recordError instanceof Error
          ? recordError.message
          : "마이크 접근에 실패했습니다.";
      setError(message);
      stopTracks();
      recorderRef.current = null;
      setRecording(false);
    }
  };

  const stopRecording = () => {
    const recorder = recorderRef.current;
    if (!recorder) {
      return;
    }
    if (recorder.state === "recording") {
      recorder.stop();
    }
    setRecording(false);
  };

  return (
    <div style={{ display: "grid", gap: "8px" }}>
      <div style={{ display: "flex", gap: "8px", flexWrap: "wrap" }}>
        <button
          type="button"
          className="btn-secondary-sm"
          onClick={recording ? stopRecording : startRecording}
          disabled={disabled || loading || !canRecord}
        >
          {recording ? "녹음 종료" : "음성 녹음"}
        </button>
        <button
          type="button"
          className="btn-secondary-sm"
          onClick={openFilePicker}
          disabled={disabled || loading}
        >
          음성 파일 업로드
        </button>
        <input
          ref={fileInputRef}
          type="file"
          accept="audio/*"
          onChange={handleFileChange}
          style={{ display: "none" }}
        />
      </div>
      {!canRecord && (
        <small style={{ color: "var(--muted)" }}>
          이 브라우저는 녹음을 지원하지 않아 파일 업로드만 사용 가능합니다.
        </small>
      )}
      {error && <small style={{ color: "#fda4af" }}>{error}</small>}
    </div>
  );
}
