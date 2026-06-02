"use client";
import { useEffect, useRef } from "react";
import ReactMarkdown from "react-markdown";
import { X, Download } from "lucide-react";

interface Props {
  title: string;
  content: string;
  onClose: () => void;
  onDownload: () => void;
}

export function DocViewer({ title, content, onClose, onDownload }: Props) {
  const ref = useRef<HTMLDivElement>(null);

  // Close on Escape
  useEffect(() => {
    const handler = (e: KeyboardEvent) => { if (e.key === "Escape") onClose(); };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [onClose]);

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-black/40 z-40"
        onClick={onClose}
      />

      {/* Drawer */}
      <div
        ref={ref}
        className="fixed bottom-0 left-0 right-0 z-50 flex flex-col"
        style={{
          height: "72vh",
          background: "#0f172a",
          borderTop: "1px solid #1e293b",
          borderRadius: "12px 12px 0 0",
          boxShadow: "0 -8px 40px rgba(0,0,0,0.6)",
          animation: "slideUp 0.22s ease-out",
        }}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-3 border-b border-gray-800 flex-shrink-0">
          <span className="text-sm font-semibold text-gray-200">{title}</span>
          <div className="flex items-center gap-2">
            <button
              onClick={onDownload}
              className="flex items-center gap-1.5 px-3 py-1.5 bg-blue-600 hover:bg-blue-500 text-white text-xs rounded-md transition-colors"
            >
              <Download size={13} />
              Download .md
            </button>
            <button
              onClick={onClose}
              className="p-1.5 text-gray-500 hover:text-gray-200 rounded hover:bg-gray-800 transition-colors"
            >
              <X size={16} />
            </button>
          </div>
        </div>

        {/* Body */}
        <div className="flex-1 overflow-y-auto px-8 py-6">
          <div className="max-w-4xl mx-auto prose prose-invert prose-sm
            prose-headings:text-gray-100 prose-headings:font-semibold
            prose-p:text-gray-300 prose-p:leading-relaxed
            prose-strong:text-gray-100
            prose-code:text-blue-300 prose-code:bg-gray-800 prose-code:px-1 prose-code:rounded
            prose-pre:bg-gray-800 prose-pre:border prose-pre:border-gray-700
            prose-li:text-gray-300
            prose-a:text-blue-400
            prose-hr:border-gray-700
            prose-table:text-gray-300
            prose-th:text-gray-200 prose-th:border-gray-700
            prose-td:border-gray-700">
            <ReactMarkdown>{content}</ReactMarkdown>
          </div>
        </div>
      </div>

      <style>{`
        @keyframes slideUp {
          from { transform: translateY(100%); }
          to   { transform: translateY(0); }
        }
      `}</style>
    </>
  );
}
