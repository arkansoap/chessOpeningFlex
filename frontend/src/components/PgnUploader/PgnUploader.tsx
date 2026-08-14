import { useCallback, useRef, useState } from "react";
import { chesscom } from "../../services/api";
import type { ImportedGame } from "../../types";

export interface PgnUploaderProps {
  /** Called once the upload succeeds with the imported games. */
  onImported?: (games: ImportedGame[]) => void;
  /** Show a textarea fallback in addition to drag & drop. */
  enableTextarea?: boolean;
}

/**
 * Drag & drop PGN uploader. Reads the file client-side and POSTs the raw
 * text to /api/v1/chesscom/upload-pgn.
 */
export default function PgnUploader({
  onImported,
  enableTextarea = true,
}: PgnUploaderProps) {
  const [dragging, setDragging] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [textareaValue, setTextareaValue] = useState("");
  const inputRef = useRef<HTMLInputElement>(null);

  const upload = useCallback(
    async (pgn: string) => {
      if (!pgn.trim()) {
        setError("Le PGN est vide.");
        return;
      }
      setLoading(true);
      setError(null);
      try {
        const games = await chesscom.uploadPgn(pgn);
        onImported?.(games);
        setTextareaValue("");
      } catch (e: unknown) {
        setError(messageFromError(e));
      } finally {
        setLoading(false);
      }
    },
    [onImported]
  );

  const handleFile = useCallback(
    (file: File) => {
      const reader = new FileReader();
      reader.onload = () => {
        const text = typeof reader.result === "string" ? reader.result : "";
        void upload(text);
      };
      reader.onerror = () => setError("Lecture du fichier impossible.");
      reader.readAsText(file);
    },
    [upload]
  );

  const onDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setDragging(false);
      const file = e.dataTransfer.files?.[0];
      if (file) handleFile(file);
    },
    [handleFile]
  );

  return (
    <div className="pgn-uploader">
      <div
        className={`dropzone${dragging ? " dropzone--active" : ""}`}
        onDragOver={(e) => {
          e.preventDefault();
          setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={onDrop}
        onClick={() => inputRef.current?.click()}
        style={{
          border: "2px dashed #9ca3af",
          borderRadius: 8,
          padding: "2rem",
          textAlign: "center",
          cursor: "pointer",
          background: dragging ? "#f3f4f6" : "transparent",
        }}
      >
        <p>
          {loading
            ? "Import en cours…"
            : "Glissez-déposez un fichier PGN ici, ou cliquez pour parcourir."}
        </p>
        <input
          ref={inputRef}
          type="file"
          accept=".pgn,.txt"
          style={{ display: "none" }}
          onChange={(e) => {
            const file = e.target.files?.[0];
            if (file) handleFile(file);
          }}
        />
      </div>

      {enableTextarea && (
        <div style={{ marginTop: "1rem" }}>
          <textarea
            placeholder="…ou collez directement le contenu PGN"
            value={textareaValue}
            onChange={(e) => setTextareaValue(e.target.value)}
            rows={6}
            style={{ width: "100%", fontFamily: "monospace" }}
          />
          <button
            type="button"
            disabled={loading || !textareaValue.trim()}
            onClick={() => upload(textareaValue)}
          >
            Importer le PGN
          </button>
        </div>
      )}

      {error && <p style={{ color: "#dc2626" }}>Erreur : {error}</p>}
    </div>
  );
}

function messageFromError(e: unknown): string {
  if (e && typeof e === "object" && "response" in e) {
    const resp = (e as { response?: { data?: { detail?: string } } }).response;
    return resp?.data?.detail ?? "Échec de l'import.";
  }
  return "Échec de l'import.";
}
