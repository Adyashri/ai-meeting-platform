"use client";

import { useState, useEffect, useRef, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { io, Socket } from "socket.io-client";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const WS_BASE  = API_BASE.replace("https://", "wss://").replace("http://", "ws://");

type Participant = { sid: string; user_name: string; user_id: string; };
type ChatMessage = { user_name: string; message: string; timestamp: string; };

function MeetingPageContent() {
  const router       = useRouter();
  const searchParams = useSearchParams();
  const meetingId    = searchParams.get("id");
  const roomCode     = searchParams.get("code");

  const [meetingStatus,   setMeetingStatus]   = useState("scheduled");
  const [isRecording,     setIsRecording]     = useState(false);
  const [transcript,      setTranscript]      = useState<string[]>([]);
  const [status,          setStatus]          = useState("");
  const [loading,         setLoading]         = useState(false);
  const [participants,    setParticipants]    = useState<Participant[]>([]);
  const [chatMessages,    setChatMessages]    = useState<ChatMessage[]>([]);
  const [chatInput,       setChatInput]       = useState("");
  const [socketConnected, setSocketConnected] = useState(false);

  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const websocketRef     = useRef<WebSocket | null>(null);
  const streamRef        = useRef<MediaStream | null>(null);
  const socketRef        = useRef<Socket | null>(null);
  const recognitionRef   = useRef<any>(null);

  const userName = typeof window !== "undefined" ? localStorage.getItem("userName") || "Unknown" : "Unknown";
  const userId   = typeof window !== "undefined" ? localStorage.getItem("userId")   || ""        : "";

  useEffect(() => {
    const token = localStorage.getItem("token");
    if (!token)   { router.push("/login"); return; }
    if (!roomCode) return;

    const socket = io(API_BASE, { transports: ["websocket", "polling"], reconnection: true });
    socketRef.current = socket;

    socket.on("connect",      () => { setSocketConnected(true); socket.emit("join_room", { room_code: roomCode, user_name: userName, user_id: userId }); });
    socket.on("disconnect",   () => setSocketConnected(false));
    socket.on("room_joined",  (data: any) => setParticipants(data.participants || []));
    socket.on("user_joined",  (data: any) => { setParticipants(data.participants || []); setStatus(`${data.user_name} joined`); });
    socket.on("user_left",    (data: any) => { setParticipants(data.participants || []); setStatus(`${data.user_name} left`); });
    socket.on("new_message",  (data: ChatMessage) => setChatMessages(prev => [...prev, data]));
    socket.on("meeting_ended",() => { setStatus("Meeting has ended!"); setMeetingStatus("ended"); });

    return () => { socket.emit("leave_room", { room_code: roomCode }); socket.disconnect(); };
  }, [roomCode]);

  const startMeeting = async () => {
    if (!meetingId) return;
    setLoading(true);
    try {
      const token = localStorage.getItem("token");
      const res   = await fetch(`${API_BASE}/meeting/start/${meetingId}`, { method: "POST", headers: { Authorization: `Bearer ${token}` } });
      const data  = await res.json();
      if (res.ok) { setMeetingStatus("active"); setStatus("Meeting started!"); }
      else alert(data.detail || "Meeting start failed");
    } catch { alert("Server error!"); }
    finally { setLoading(false); }
  };

  const saveTranscriptToBackend = async (text: string) => {
    if (!meetingId) return;
    try {
      const token = localStorage.getItem("token");
      await fetch(`${API_BASE}/transcription/save`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          meeting_id: meetingId,
          speaker_name: userName,
          text: text,
        }),
      });
    } catch (e) {
      console.log("Transcript save failed:", e);
    }
  };
const startRecording = async () => {
    if (!meetingId || isRecording) return;
    try {
      const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
      if (!SpeechRecognition) {
        alert("Speech recognition only works in the Chrome browser.");
        return;
      }
      const recognition = new SpeechRecognition();
      recognition.continuous = true;
      recognition.interimResults = false;
      recognition.lang = "en-US";

      recognition.onresult = (event: any) => {
      const result = event.results[event.results.length - 1];
      const text = result[0].transcript.trim();
      if (text) {
        setTranscript(prev => [...prev, `[${userName}]: ${text}`]);
        saveTranscriptToBackend(text);
      }
    };
      recognition.onerror = () => setStatus("Transcription error!");
      recognition.onend = () => { if (isRecording) recognition.start(); };

      recognition.start();
      recognitionRef.current = recognition;
      setIsRecording(true);
      setStatus("Recording started... speak now!");
    } catch {
      alert("Please allow microphone access.");
      setStatus("");
    }
  };

  const stopRecordingOnly = async () => {
    try {
      if (recognitionRef.current) {
        recognitionRef.current.onend = null;
        recognitionRef.current.stop();
        recognitionRef.current = null;
      }
      setIsRecording(false);
      setStatus("Recording stopped!");
    } catch {
      setStatus("Error while stopping recording");
    }
  };

  const endMeeting = async () => {
    if (!meetingId) return;
    if (isRecording) { await stopRecordingOnly(); await new Promise(r => setTimeout(r, 1000)); }
    if (socketRef.current && roomCode) socketRef.current.emit("meeting_ended", { room_code: roomCode });
    setLoading(true);
    try {
      const token = localStorage.getItem("token");
      const res   = await fetch(`${API_BASE}/meeting/end/${meetingId}`, { method: "POST", headers: { Authorization: `Bearer ${token}` } });
      if (res.ok) { setMeetingStatus("ended"); setStatus("Meeting ended!"); router.push(`/mom?meeting_id=${meetingId}`); }
      else { const data = await res.json(); alert(data.detail || "Meeting end failed"); }
    } catch { alert("Server error!"); }
    finally { setLoading(false); }
  };

  const sendChat = () => {
    if (!chatInput.trim() || !roomCode || !socketRef.current) return;
    socketRef.current.emit("send_chat", { room_code: roomCode, message: chatInput.trim(), user_name: userName });
    setChatInput("");
  };

  return (
    <div className="min-h-screen p-6" style={{ background: "#0f1117" }}>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-white">Meeting Room</h1>
          <div className="flex items-center gap-3 mt-1">
            {roomCode && <span className="text-xs px-2.5 py-1 rounded-lg font-mono" style={{ background: "#252c3f", color: "#6b7fff" }}>{roomCode}</span>}
            <div className="flex items-center gap-1.5">
              <div className="w-2 h-2 rounded-full" style={{ background: socketConnected ? "#22c55e" : "#ef4444" }} />
              <span className="text-xs" style={{ color: "#8892a4" }}>{socketConnected ? "Connected" : "Connecting..."}</span>
            </div>
          </div>
        </div>
        <button onClick={() => router.push("/dashboard")} className="px-4 py-2 rounded-xl text-sm font-medium text-white hover:opacity-80" style={{ background: "#1e2436", border: "1px solid #2a3450" }}>← Dashboard</button>
      </div>

      {status && <div className="mb-5 px-4 py-3 rounded-xl text-sm font-medium" style={{ background: "rgba(58,79,247,0.15)", border: "1px solid rgba(58,79,247,0.3)", color: "#6b7fff" }}>{status}</div>}

      <div className="grid grid-cols-3 gap-5">
        <div className="col-span-2 space-y-5">
          <div className="p-5 rounded-2xl" style={{ background: "#161a24", border: "1px solid #1e2436" }}>
            <div className="flex items-center gap-3 mb-5">
              <div className="w-3 h-3 rounded-full" style={{ background: meetingStatus === "active" ? "#22c55e" : meetingStatus === "ended" ? "#ef4444" : "#f59e0b" }} />
              <span className="text-sm font-medium text-white capitalize">{meetingStatus}</span>
            </div>
            <div className="flex flex-wrap gap-3">
              {meetingStatus === "scheduled" && <button onClick={startMeeting} disabled={loading} className="px-5 py-2.5 rounded-xl font-semibold text-sm text-white disabled:opacity-50" style={{ background: "linear-gradient(135deg, #3a4ff7 0%, #5c69fa 100%)" }}>{loading ? "Starting..." : "▶ Start Meeting"}</button>}
              {meetingStatus === "active" && !isRecording && <button onClick={startRecording} className="px-5 py-2.5 rounded-xl font-semibold text-sm text-white hover:opacity-80" style={{ background: "#22c55e" }}>🎙 Start Recording</button>}
              {meetingStatus === "active" && isRecording  && <button onClick={stopRecordingOnly} className="px-5 py-2.5 rounded-xl font-semibold text-sm text-white hover:opacity-80" style={{ background: "#f59e0b" }}>⏹ Stop Recording</button>}
              {meetingStatus === "active" && <button onClick={endMeeting} disabled={loading} className="px-5 py-2.5 rounded-xl font-semibold text-sm text-white disabled:opacity-50" style={{ background: "#ef4444" }}>{loading ? "Ending..." : "⬛ End Meeting"}</button>}
            </div>
          </div>

          <div className="p-5 rounded-2xl" style={{ background: "#161a24", border: "1px solid #1e2436" }}>
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-sm font-semibold text-white">Live Transcript</h2>
              {isRecording && <div className="flex items-center gap-2"><div className="w-2 h-2 rounded-full animate-pulse" style={{ background: "#ef4444" }} /><span className="text-xs" style={{ color: "#ef4444" }}>Recording</span></div>}
            </div>
            {transcript.length === 0
              ? <p className="text-sm py-6 text-center" style={{ color: "#8892a4" }}>{isRecording ? "Listening... start speaking!" : "Start recording to see live transcript."}</p>
              : <div className="space-y-2 max-h-60 overflow-y-auto">{transcript.map((line, i) => <div key={i} className="p-3 rounded-xl text-sm" style={{ borderLeft: "3px solid #3a4ff7", background: "#1e2436", color: "#e8eaf0" }}>{line}</div>)}</div>
            }
          </div>
        </div>

        <div className="space-y-5">
          <div className="p-5 rounded-2xl" style={{ background: "#161a24", border: "1px solid #1e2436" }}>
            <h2 className="text-sm font-semibold text-white mb-3">Participants ({participants.length})</h2>
            {participants.length === 0
              ? <p className="text-xs" style={{ color: "#8892a4" }}>No one yet</p>
              : <div className="space-y-2">{participants.map((p, i) => <div key={i} className="flex items-center gap-2"><div className="w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold" style={{ background: "rgba(58,79,247,0.25)", color: "#6b7fff" }}>{p.user_name?.[0]?.toUpperCase() || "U"}</div><span className="text-xs text-white truncate">{p.user_name}</span></div>)}</div>
            }
          </div>

          <div className="p-5 rounded-2xl flex flex-col" style={{ background: "#161a24", border: "1px solid #1e2436", minHeight: "280px" }}>
            <h2 className="text-sm font-semibold text-white mb-3">Meeting Chat</h2>
            <div className="flex-1 space-y-2 max-h-48 overflow-y-auto mb-3">
              {chatMessages.length === 0
                ? <p className="text-xs" style={{ color: "#8892a4" }}>No messages yet</p>
                : chatMessages.map((msg, i) => <div key={i} className="text-xs"><span style={{ color: "#6b7fff" }}>{msg.user_name}: </span><span className="text-white">{msg.message}</span></div>)
              }
            </div>
            <div className="flex gap-2">
              <input type="text" placeholder="Type a message..." value={chatInput} onChange={e => setChatInput(e.target.value)} onKeyDown={e => e.key === "Enter" && sendChat()} className="flex-1 rounded-xl px-3 py-2 text-xs text-white placeholder:text-[#4a5568]" style={{ background: "#252c3f", border: "1px solid #1e2436" }} />
              <button onClick={sendChat} className="px-3 py-2 rounded-xl text-xs font-semibold text-white hover:opacity-80" style={{ background: "#3a4ff7" }}>Send</button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default function MeetingPage() {
  return (
    <Suspense fallback={
      <div className="min-h-screen flex items-center justify-center" style={{ background: "#0f1117" }}>
        <div className="w-8 h-8 border-2 rounded-full animate-spin" style={{ borderColor: "#6b7fff", borderTopColor: "transparent" }} />
      </div>
    }>
      <MeetingPageContent />
    </Suspense>
  );
}