"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

type Meeting = {
  id: string;
  title: string;
  room_code: string;
  status: string;
  started_at?: string | null;
  ended_at?: string | null;
};

export default function DashboardPage() {
  const router = useRouter();
  const [userName, setUserName]           = useState("");
  const [meetings, setMeetings]           = useState<Meeting[]>([]);
  const [loadingMeetings, setLoadingMeetings] = useState(true);
  const [creatingMeeting, setCreatingMeeting] = useState(false);
  const [roomCode, setRoomCode]           = useState("");

  useEffect(() => {
    const token = localStorage.getItem("token");
    const name  = localStorage.getItem("userName");
    if (!token) { router.replace("/login"); return; }
    if (name) setUserName(name);
    fetchMyMeetings(token);
  }, [router]);

  const handleUnauthorized = () => {
    localStorage.clear();
    router.replace("/login");
  };

  const fetchMyMeetings = async (tokenArg?: string) => {
    const token = tokenArg || localStorage.getItem("token");
    if (!token) { handleUnauthorized(); return; }
    try {
      setLoadingMeetings(true);
      // ✅ Correct endpoint
      const response = await fetch(`${API_BASE}/meeting/list`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (response.status === 401) { handleUnauthorized(); return; }
      if (!response.ok) { setMeetings([]); return; }
      const data = await response.json();
      setMeetings(Array.isArray(data) ? data : data.meetings || []);
    } catch {
      setMeetings([]);
    } finally {
      setLoadingMeetings(false);
    }
  };

  const createMeeting = async () => {
    const token = localStorage.getItem("token");
    if (!token) { handleUnauthorized(); return; }
    try {
      setCreatingMeeting(true);
      const response = await fetch(`${API_BASE}/meeting/create`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ title: "New Meeting" }),
      });
      if (response.status === 401) { handleUnauthorized(); return; }
      const data = await response.json();
      if (!response.ok) { alert(data.detail || "Meeting creation failed"); return; }
      fetchMyMeetings(token);
      router.push(`/meeting?id=${data.meeting_id}&code=${data.room_code}`);
    } catch {
      alert("Meeting creation failed");
    } finally {
      setCreatingMeeting(false);
    }
  };

  const joinMeeting = () => {
    if (!roomCode.trim()) { alert("Please enter a room code!"); return; }
    router.push(`/meeting?code=${roomCode.trim()}`);
  };

  return (
    <div className="min-h-screen" style={{ background: "#0f1117" }}>
      {/* Navbar */}
      <nav className="flex items-center justify-between px-8 py-4"
           style={{ background: "#161a24", borderBottom: "1px solid #1e2436" }}>
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-xl flex items-center justify-center"
               style={{ background: "linear-gradient(135deg, #3a4ff7 0%, #6b7fff 100%)" }}>
            <span className="text-white font-bold text-sm">AI</span>
          </div>
          <span className="text-white font-bold">AI Meeting Platform</span>
        </div>
        <div className="flex items-center gap-4">
          <span className="text-sm" style={{ color: "#8892a4" }}>{userName}</span>
          <button
            onClick={() => { localStorage.clear(); router.replace("/login"); }}
            className="px-4 py-2 rounded-xl text-sm font-medium text-white hover:opacity-80 transition-all"
            style={{ background: "#252c3f", border: "1px solid #1e2436" }}>
            Logout
          </button>
        </div>
      </nav>

      <div className="p-8 max-w-6xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-white">
            Welcome Back{userName ? `, ${userName.split(" ")[0]}` : ""}! 👋
          </h1>
          <p className="mt-1 text-sm" style={{ color: "#8892a4" }}>Manage your meetings here</p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-5 mb-6">
          {/* Create Meeting */}
          <div className="p-6 rounded-2xl" style={{ background: "#161a24", border: "1px solid #1e2436" }}>
            <h2 className="text-base font-semibold text-white mb-1">New Meeting</h2>
            <p className="text-sm mb-5" style={{ color: "#8892a4" }}>
              Create and start a new meeting instantly
            </p>
            <button
              onClick={createMeeting}
              disabled={creatingMeeting}
              className="w-full py-2.5 rounded-xl text-sm font-semibold text-white disabled:opacity-50 transition-all"
              style={{ background: "linear-gradient(135deg, #3a4ff7 0%, #5c69fa 100%)" }}>
              {creatingMeeting ? "Creating..." : "+ Create Meeting"}
            </button>
          </div>

          {/* Quick Join */}
          <div className="p-6 rounded-2xl" style={{ background: "#161a24", border: "1px solid #1e2436" }}>
            <h2 className="text-base font-semibold text-white mb-1">Quick Join</h2>
            <p className="text-sm mb-4" style={{ color: "#8892a4" }}>Enter room code to join</p>
            <input
              type="text"
              placeholder="Enter Room Code"
              value={roomCode}
              onChange={e => setRoomCode(e.target.value)}
              onKeyDown={e => e.key === "Enter" && joinMeeting()}
              className="w-full rounded-xl px-4 py-2.5 text-sm text-white placeholder:text-[#4a5568] mb-3"
              style={{ background: "#252c3f", border: "1px solid #1e2436" }}
            />
            <button
              onClick={joinMeeting}
              className="w-full py-2.5 rounded-xl text-sm font-semibold text-white hover:opacity-80 transition-all"
              style={{ background: "#22c55e" }}>
              Join Now
            </button>
          </div>

          {/* Stats */}
          <div className="p-6 rounded-2xl" style={{ background: "#161a24", border: "1px solid #1e2436" }}>
            <h2 className="text-base font-semibold text-white mb-4">Your Statistics</h2>
            <div className="grid grid-cols-2 gap-3">
              {[
                { label: "Total Meetings", value: meetings.length, color: "#3a4ff7" },
                { label: "Active",         value: meetings.filter(m => m.status === "active").length, color: "#22c55e" },
                { label: "Ended",          value: meetings.filter(m => m.status === "ended").length,  color: "#a855f7" },
                { label: "Recordings",     value: 0, color: "#f59e0b" },
              ].map(({ label, value, color }) => (
                <div key={label} className="p-3 rounded-xl text-center"
                     style={{ background: "#252c3f" }}>
                  <p className="text-2xl font-bold" style={{ color }}>{value}</p>
                  <p className="text-xs mt-0.5" style={{ color: "#8892a4" }}>{label}</p>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* My Meetings List */}
        <div className="p-6 rounded-2xl" style={{ background: "#161a24", border: "1px solid #1e2436" }}>
          <div className="flex items-center justify-between mb-5">
            <h2 className="text-base font-semibold text-white">My Meetings</h2>
            <button
              onClick={() => fetchMyMeetings()}
              className="text-xs px-3 py-1.5 rounded-lg hover:opacity-80 transition-all"
              style={{ background: "#252c3f", color: "#8892a4" }}>
              Refresh
            </button>
          </div>

          {loadingMeetings ? (
            <p className="text-sm py-6 text-center" style={{ color: "#8892a4" }}>Loading meetings...</p>
          ) : meetings.length === 0 ? (
            <p className="text-sm py-6 text-center" style={{ color: "#8892a4" }}>
              No meetings yet — click "Create Meeting" to start!
            </p>
          ) : (
            <div className="space-y-3">
              {meetings.map((meeting) => (
                <div key={meeting.id}
                     className="flex items-center justify-between p-4 rounded-xl"
                     style={{ background: "#1e2436", border: "1px solid #252c3f" }}>
                  <div>
                    <p className="text-sm font-semibold text-white">{meeting.title}</p>
                    <p className="text-xs mt-0.5" style={{ color: "#8892a4" }}>
                      Room: {meeting.room_code} &nbsp;·&nbsp;
                      <span style={{
                        color: meeting.status === "active" ? "#22c55e"
                             : meeting.status === "ended"  ? "#8892a4"
                             : "#f59e0b"
                      }}>
                        {meeting.status}
                      </span>
                    </p>
                  </div>
                  <div className="flex gap-2">
                    {meeting.status !== "ended" && (
                      <button
                        onClick={() => router.push(`/meeting?id=${meeting.id}&code=${meeting.room_code}`)}
                        className="px-3 py-1.5 rounded-lg text-xs font-semibold text-white hover:opacity-80"
                        style={{ background: "#3a4ff7" }}>
                        Join
                      </button>
                    )}
                    <button
                      onClick={() => router.push(`/mom?meeting_id=${meeting.id}`)}
                      className="px-3 py-1.5 rounded-lg text-xs font-semibold hover:opacity-80"
                      style={{ background: "#252c3f", color: "#8892a4" }}>
                      View MOM
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}