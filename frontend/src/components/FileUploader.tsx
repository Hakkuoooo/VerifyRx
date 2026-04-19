"use client";

import { useState, useRef, type DragEvent, type ChangeEvent } from "react";
import { Upload, X } from "lucide-react";

interface FileUploaderProps {
  onFileSelect: (file: File) => void;
  accept?: string;
  maxSizeMB?: number;
}

export default function FileUploader({
  onFileSelect,
  accept = "image/*",
  maxSizeMB = 10,
}: FileUploaderProps) {
  const [dragOver, setDragOver] = useState(false);
  const [preview, setPreview] = useState<string | null>(null);
  const [fileName, setFileName] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  function handleFile(file: File) {
    setError(null);
    if (file.size > maxSizeMB * 1024 * 1024) {
      setError(`File too large. Maximum size is ${maxSizeMB}MB.`);
      return;
    }
    if (!file.type.startsWith("image/")) {
      setError("Only image files are accepted.");
      return;
    }
    if (preview) URL.revokeObjectURL(preview);
    setFileName(file.name);
    setPreview(URL.createObjectURL(file));
    onFileSelect(file);
  }

  function handleDrop(e: DragEvent) {
    e.preventDefault();
    setDragOver(false);
    const file = e.dataTransfer.files[0];
    if (file) handleFile(file);
  }

  function handleChange(e: ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (file) handleFile(file);
  }

  function clear() {
    if (preview) URL.revokeObjectURL(preview);
    setPreview(null);
    setFileName(null);
    setError(null);
    if (inputRef.current) inputRef.current.value = "";
  }

  return (
    <div>
      {preview ? (
        <div className="relative bg-white border border-[var(--color-line)] p-4">
          <button
            onClick={clear}
            className="absolute top-2 right-2 p-1 hover:bg-[var(--color-line)] transition-colors"
            aria-label="Remove file"
          >
            <X className="w-4 h-4 text-[var(--color-ink-muted)]" />
          </button>
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src={preview}
            alt="Upload preview"
            className="max-h-64 mx-auto object-contain"
          />
          <p className="text-sm text-[var(--color-ink-muted)] text-center mt-3 font-mono text-[13px]">
            {fileName}
          </p>
        </div>
      ) : (
        <div
          onClick={() => inputRef.current?.click()}
          onDragOver={(e) => {
            e.preventDefault();
            setDragOver(true);
          }}
          onDragLeave={() => setDragOver(false)}
          onDrop={handleDrop}
          role="button"
          tabIndex={0}
          onKeyDown={(e) => {
            if (e.key === "Enter" || e.key === " ") {
              e.preventDefault();
              inputRef.current?.click();
            }
          }}
          className={`border-2 border-dashed p-8 text-center cursor-pointer transition-colors ${
            dragOver
              ? "border-[var(--color-primary)] bg-[var(--color-primary-light)]"
              : "border-[var(--color-line-strong)] hover:border-[var(--color-primary)] bg-white"
          }`}
        >
          <Upload
            className="w-8 h-8 text-[var(--color-ink-faint)] mx-auto mb-3"
            aria-hidden
          />
          <p className="text-sm font-semibold text-[var(--color-ink)]">
            Drop a photo here, or click to choose a file
          </p>
          <p className="text-xs text-[var(--color-ink-faint)] mt-1">
            JPG, PNG or WebP &middot; up to {maxSizeMB} MB
          </p>
        </div>
      )}
      {error && (
        <p className="text-sm text-[var(--color-danger)] mt-3 font-medium">
          {error}
        </p>
      )}
      <input
        ref={inputRef}
        type="file"
        accept={accept}
        onChange={handleChange}
        className="hidden"
      />
    </div>
  );
}
