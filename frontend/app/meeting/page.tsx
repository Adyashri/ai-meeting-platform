"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import Navbar from "@/components/Navbar";

export default function MeetingPage() {
  const router = useRouter();
  const [muted, setMuted] = useState(false);
  const [camera, setCamera] = useState(true);
  const [chat, setChat] = useState(false);

  return (
    <div className="min-h-screen bg-gray-900 text-white">
      <Navbar />
      <div className="p-4">
        <div className="grid grid-cols-2 gap-4 mb-4">
          <div className="bg-gray-800 rounded-xl h-64 flex flex-col items-center justify-center border-2 border-blue-500">
            <p className="text-4xl mb-2">👤</p>
            <p className="text-gray-400">You</p>
            {muted && <p className="text-red-400 text-sm mt-1">🔇 Muted</p>}
          </div>
          <div className="bg-gray-800 rounded-xl h-64 flex flex-col items-center justify-center">
            <p className="text-4xl mb-2">👤</p>
            <p className="text-gray-400">Participant</p>
          </div>
        </div>
        {chat && (
          <div className="bg-gray-800 rounded-xl p-4 mb-4 h-40">
            <h3 className="font-semibold mb-2">💬 Chat</h3>
            <p className="text-gray-400 text-sm">No messages yet...</p>
          </div>
        )}
        <div className="flex justify-center gap-4 mt-4">
          <button onClick={() => setMuted(!muted)}
            className={`px-6 py-3 rounded-xl ${muted ? "bg-red-600" : "bg-gray-700"}`}>
            {muted ? "🔇 Unmute" : "🎤 Mute"}
          </button>
          <button onClick={() => setCamera(!camera)}
            className={`px-6 py-3 rounded-xl ${!camera ? "bg-red-600" : "bg-gray-700"}`}>
            {camera ? "📷 Camera" : "📷 Off"}
          </button>
          <button onClick={() => setChat(!chat)}
            className="bg-gray-700 px-6 py-3 rounded-xl">
            💬 Chat
          </button>
          <button className="bg-gray-700 px-6 py-3 rounded-xl">
            🖥️ Share
          </button>
          <button onClick={() => router.push("/dashboard")}
            className="bg-red-600 px-6 py-3 rounded-xl">
            📵 End Call
          </button>
        </div>
      </div>
    </div>
  );
}