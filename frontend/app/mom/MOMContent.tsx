"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

type TranscriptItem = {
  id: string;
  text: string;
  start_time: number;
  end_time: number;
  language: string;
  meeting_id: string;
  speaker_name: string;
  created_at: string;
};

type MOMData = {
  summary?: string;
  key_discussions?: { topic: string; details: string }[];
  decisions?: { decision: string; reason: string }[];
  action_items?: {
    task: string;
    assigned_to: string;
    deadline: string;
    priority: string;
  }[];
  next_meeting?: string;
};

export default function MOMContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const urlMeetingId = searchParams.get("meeting_id");

  const [meetingId, setMeetingId] = useState("");
  const [mom, setMom] = useState<MOMData | null>(null);
  const [transcripts, setTranscripts] = useState<TranscriptItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [transcriptLoading, setTranscriptLoading] = useState(false);
  const [error, setError] = useState("");
  const [status, setStatus] = useState("");

  const autoTriggeredRef = useRef(false);

  useEffect(() => {
    const token = localStorage.getItem("token");
    if (!token) { router.push("/login"); return; }
    if (urlMeetingId) setMeetingId(urlMeetingId);
  }, [urlMeetingId, router]);

  useEffect(() => {
    if (!meetingId) return;
    if (!autoTriggeredRef.current) {
      autoTriggeredRef.current = true;
      handleGenerateAll(meetingId);
    }
  }, [meetingId]);

  const fetchTranscript = async (id?: string) => {
    const finalId = id || meetingId;
    if (!finalId) return;
    try {
      setTranscriptLoading(true);
      setError("");
      const token = localStorage.getItem("token");
      const response = await fetch(`${API_BASE}/transcription/${finalId}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!response.ok) { setTranscripts([]); return; }
      const data = await response.json();
      setTranscripts(Array.isArray(data) ? data : Array.isArray(data?.transcripts) ? data.transcripts : []);
    } catch {
      setTranscripts([]);
    } finally {
      setTranscriptLoading(false);
    }
  };

  const generateMOM = async (id?: string) => {
    const finalId = id || meetingId;
    if (!finalId) { setError("Meeting ID missing!"); return; }
    try {
      setLoading(true);
      setError("");
      setStatus("Generating MOM with AI...");
      const token = localStorage.getItem("token");
      const response = await fetch(`${API_BASE}/mom/generate/${finalId}`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
      });
      const data = await response.json();
      if (!response.ok) {
        setError(data.detail || "MOM generation failed");
        setStatus("");
        return;
      }
      setMom(data.mom ? data.mom : data);
      setStatus("MOM generated successfully!");
    } catch {
      setError("MOM generation failed. Check if backend is running.");
      setStatus("");
    } finally {
      setLoading(false);
    }
  };

  const handleGenerateAll = async (id?: string) => {
    const finalId = id || meetingId;
    if (!finalId) { setError("Meeting ID missing!"); return; }
    setError("");
    setStatus("Loading transcript + generating MOM...");
    await fetchTranscript(finalId);
    await generateMOM(finalId);
  };

  const downloadFile = async (type: "pdf" | "docx") => {
    if (!meetingId) return;
    try {
      const token = localStorage.getItem("token");
      const response = await fetch(`${API_BASE}/download/${type}/${meetingId}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!response.ok) { alert(`${type.toUpperCase()} download failed!`); return; }
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `MOM_${meetingId}.${type}`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
    } catch {
      alert(`Server error while downloading ${type.toUpperCase()}!`);
    }
  };

  return (
    <div className="min-h-screen p-8" style={{ background: "#0f1117" }}>
      {/* Header */}
      <div className="flex justify-between items-center mb-8">
        <div>
          <h1 className="text-3xl font-bold text-white">Minutes of Meeting</h1>
          <p className="mt-1" style={{ color: "#8892a4" }}>AI-powered meeting summary</p>
        </div>
        <button onClick={() => router.push("/dashboard")}
          className="px-4 py-2 rounded-xl text-sm font-medium text-white transition-all hover:opacity-80"
          style={{ background: "#1e2436", border: "1px solid #2a3450" }}>
          ← Back to Dashboard
        </button>
      </div>

      {/* Meeting ID Input */}
      <div className="p-6 rounded-2xl mb-6" style={{ background: "#161a24", border: "1px solid #1e2436" }}>
        <h2 className="text-base font-semibold text-white mb-4">Meeting ID</h2>
        <div className="flex gap-3">
          <input
            type="text"
            placeholder="Enter meeting ID"
            value={meetingId}
            onChange={(e) => { autoTriggeredRef.current = true; setMeetingId(e.target.value); }}
            className="flex-1 rounded-xl px-4 py-3 text-sm text-white placeholder:text-[#4a5568]"
            style={{ background: "#252c3f", border: "1px solid #1e2436" }}
          />
          <button onClick={() => handleGenerateAll(meetingId)}
            disabled={loading || transcriptLoading}
            className="px-6 py-3 rounded-xl text-sm font-semibold text-white disabled:opacity-50 transition-all"
            style={{ background: "linear-gradient(135deg, #3a4ff7 0%, #5c69fa 100%)" }}>
            {loading ? "Generating..." : "Generate MOM"}
          </button>
        </div>
        {status && <p className="mt-3 text-sm font-medium" style={{ color: "#22c55e" }}>{status}</p>}
        {error && <p className="mt-3 text-sm font-medium" style={{ color: "#f87171" }}>{error}</p>}
      </div>

      {/* Transcript */}
      <div className="p-6 rounded-2xl mb-6" style={{ background: "#161a24", border: "1px solid #1e2436" }}>
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-bold text-white">Meeting Transcript</h2>
          <button onClick={() => fetchTranscript(meetingId)}
            className="px-4 py-2 rounded-xl text-xs font-medium text-white hover:opacity-80"
            style={{ background: "#252c3f" }}>
            Refresh
          </button>
        </div>
        {transcriptLoading ? (
          <p style={{ color: "#8892a4" }}>Loading transcript...</p>
        ) : transcripts.length > 0 ? (
          <div className="space-y-3 max-h-72 overflow-y-auto">
            {transcripts.map((item, index) => (
              <div key={item.id || index} className="p-3 rounded-xl"
                style={{ borderLeft: "3px solid #3a4ff7", background: "#1e2436" }}>
                <p className="text-sm font-semibold mb-1" style={{ color: "#6b7fff" }}>
                  {item.speaker_name || "Unknown"}{" "}
                  <span className="font-normal" style={{ color: "#8892a4" }}>
                    ({Number(item.start_time || 0).toFixed(1)}s — {Number(item.end_time || 0).toFixed(1)}s)
                  </span>
                </p>
                <p className="text-sm text-white">{item.text}</p>
              </div>
            ))}
          </div>
        ) : (
          <p style={{ color: "#8892a4" }}>No transcript found for this meeting.</p>
        )}
      </div>

      {/* MOM Content */}
      {mom && (
        <div className="space-y-5">
          {/* Download Buttons */}
          <div className="flex justify-end gap-3">
            <button onClick={() => downloadFile("docx")}
              className="px-5 py-2.5 rounded-xl text-sm font-semibold text-white hover:opacity-80"
              style={{ background: "#3a4ff7" }}>
              Download DOCX
            </button>
            <button onClick={() => downloadFile("pdf")}
              className="px-5 py-2.5 rounded-xl text-sm font-semibold text-white hover:opacity-80"
              style={{ background: "#22c55e" }}>
              Download PDF
            </button>
          </div>

          {/* Summary */}
          {mom.summary && (
            <div className="p-6 rounded-2xl" style={{ background: "#161a24", border: "1px solid #1e2436" }}>
              <h2 className="text-lg font-bold mb-3" style={{ color: "#6b7fff" }}>Summary</h2>
              <p className="text-sm leading-relaxed text-white">{mom.summary}</p>
            </div>
          )}

          {/* Key Discussions */}
          {mom.key_discussions?.length ? (
            <div className="p-6 rounded-2xl" style={{ background: "#161a24", border: "1px solid #1e2436" }}>
              <h2 className="text-lg font-bold mb-4" style={{ color: "#6b7fff" }}>Key Discussions</h2>
              <div className="space-y-3">
                {mom.key_discussions.map((d, i) => (
                  <div key={i} className="pl-4 py-2 rounded-r-xl"
                    style={{ borderLeft: "3px solid #3a4ff7", background: "#1e2436" }}>
                    <p className="text-sm font-semibold text-white">{d.topic}</p>
                    <p className="text-xs mt-1" style={{ color: "#8892a4" }}>{d.details}</p>
                  </div>
                ))}
              </div>
            </div>
          ) : null}

          {/* Decisions */}
          {mom.decisions?.length ? (
            <div className="p-6 rounded-2xl" style={{ background: "#161a24", border: "1px solid #1e2436" }}>
              <h2 className="text-lg font-bold mb-4" style={{ color: "#6b7fff" }}>Decisions Made</h2>
              <div className="space-y-3">
                {mom.decisions.map((d, i) => (
                  <div key={i} className="flex gap-3 items-start">
                    <span className="text-xs font-bold px-2 py-1 rounded-lg flex-shrink-0"
                      style={{ background: "rgba(58,79,247,0.2)", color: "#6b7fff" }}>
                      {i + 1}
                    </span>
                    <div>
                      <p className="text-sm font-semibold text-white">{d.decision}</p>
                      <p className="text-xs mt-1" style={{ color: "#8892a4" }}>{d.reason}</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ) : null}

          {/* Action Items */}
          {mom.action_items?.length ? (
            <div className="p-6 rounded-2xl" style={{ background: "#161a24", border: "1px solid #1e2436" }}>
              <h2 className="text-lg font-bold mb-4" style={{ color: "#6b7fff" }}>Action Items</h2>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr style={{ background: "#252c3f" }}>
                      <th className="p-3 text-left text-white rounded-tl-xl">Task</th>
                      <th className="p-3 text-left text-white">Assigned To</th>
                      <th className="p-3 text-left text-white">Deadline</th>
                      <th className="p-3 text-left text-white rounded-tr-xl">Priority</th>
                    </tr>
                  </thead>
                  <tbody>
                    {mom.action_items.map((item, i) => (
                      <tr key={i} style={{ borderBottom: "1px solid #1e2436" }}>
                        <td className="p-3 text-white">{item.task}</td>
                        <td className="p-3" style={{ color: "#8892a4" }}>{item.assigned_to}</td>
                        <td className="p-3" style={{ color: "#8892a4" }}>{item.deadline}</td>
                        <td className="p-3">
                          <span className="px-2 py-1 rounded-full text-xs font-bold"
                            style={{
                              background: item.priority === "high" ? "rgba(239,68,68,0.15)"
                                : item.priority === "medium" ? "rgba(245,158,11,0.15)"
                                : "rgba(34,197,94,0.15)",
                              color: item.priority === "high" ? "#f87171"
                                : item.priority === "medium" ? "#fbbf24"
                                : "#4ade80"
                            }}>
                            {(item.priority || "").toUpperCase()}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          ) : null}

          {/* Next Meeting */}
          {mom.next_meeting && mom.next_meeting !== "N/A" ? (
            <div className="p-6 rounded-2xl" style={{ background: "rgba(58,79,247,0.1)", border: "1px solid rgba(58,79,247,0.3)" }}>
              <h2 className="text-lg font-bold mb-2" style={{ color: "#6b7fff" }}>Next Meeting</h2>
              <p className="text-sm text-white">{mom.next_meeting}</p>
            </div>
          ) : null}
        </div>
      )}
    </div>
  );
}