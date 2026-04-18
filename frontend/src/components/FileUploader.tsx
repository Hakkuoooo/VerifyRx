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
        <div className="relative rounded-xl border border-gray-200 bg-white p-4">
          <button
            onClick={clear}
            className="absolute top-2 right-2 p-1 rounded-full bg-gray-100 hover:bg-gray-200 transition-colors"
            aria-label="Remove file"
          >
            <X className="w-4 h-4 text-gray-500" />
          </button>
          <img
            src={preview}
            alt="Upload preview"
            className="max-h-64 mx-auto rounded-lg object-contain"
          />
          <p className="text-sm text-gray-500 text-center mt-2">{fileName}</p>
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
          className={`rounded-xl border-2 border-dashed p-8 text-center cursor-pointer transition-colors ${
            dragOver
              ? "border-primary bg-primary-light"
              : "border-gray-300 hover:border-gray-400 bg-white"
          }`}
        >
          <Upload className="w-10 h-10 text-gray-400 mx-auto mb-3" />
          <p className="text-sm font-medium text-gray-700">
            Drag and drop or click to upload
          </p>
          <p className="text-xs text-gray-400 mt-1">
            Max {maxSizeMB}MB &middot; Images only
          </p>
        </div>
      )}
      {error && <p className="text-sm text-red-600 mt-2">{error}</p>}
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
