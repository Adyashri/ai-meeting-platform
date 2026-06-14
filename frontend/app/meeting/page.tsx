"use client";

import { useState, useEffect, useRef } from "react";
import { useRouter, useSearchParams } from "next/navigation";

export default function MeetingPage() {
  const router = useRouter();
  const searchParams = useSearchParams();

  const meetingId = searchParams.get("id");
  const roomCode  = searchParams.get("code");

  const [meetingStatus, setMeetingStatus] = useState("scheduled");
  const [isRecording, setIsRecording]     = useState(false);
  const [transcript, setTranscript]       = useState<string[]>([]);
  const [status, setStatus]               = useState("");
  const [loading, setLoading]             = useState(false);

  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const websocketRef     = useRef<WebSocket | null>(null);
  const chunksRef        = useRef<Blob[]>([]);

  useEffect(() => {
    const token = localStorage.getItem("token");
    if (!token) router.push("/login");
  }, []);

  const startMeeting = async () => {
    if (!meetingId) return;
    setLoading(true);
    try {
      const token = localStorage.getItem("token");
      const res = await fetch(
        `http://localhost:8000/meeting/start/${meetingId}`,
        {
          method: "POST",
          headers: { "Authorization": `Bearer ${token}` }
        }
      );
      const data = await res.json();
      if (res.ok) {
        setMeetingStatus("active");
        setStatus("Meeting started!");
      } else {
        alert(data.detail);
      }
    } catch (e) {
      alert("Server error!");
    } finally {
      setLoading(false);
    }
  };

  const endMeeting = async () => {
    if (!meetingId) return;
    
    // Recording band karo pehle
    if (isRecording) stopRecording();
    
    setLoading(true);
    try {
      const token = localStorage.getItem("token");
      const res = await fetch(
        `http://localhost:8000/meeting/end/${meetingId}`,
        {
          method: "POST",
          headers: { "Authorization": `Bearer ${token}` }
        }
      );
      if (res.ok) {
        setMeetingStatus("ended");
        alert("Meeting ended! Ab MOM generate karo.");
        router.push(
          `/mom?meeting_id=${meetingId}`
        );
      }
    } catch (e) {
      alert("Server error!");
    } finally {
      setLoading(false);
    }
  };

  const startRecording = async () => {
    try {
      // Microphone permission lo
      const stream = await navigator.mediaDevices.getUserMedia(
        { audio: true }
      );

      // WebSocket se backend se connect karo
      const userName = localStorage.getItem("userName") || "Unknown";
      const ws = new WebSocket(
        `ws://localhost:8000/transcription/ws/${meetingId}?speaker_name=${userName}`
      );

      ws.onopen = () => {
        console.log("Transcription connected!");
        setStatus("Recording started...");
      };

      ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        // Transcript mein add karo
        setTranscript(prev => [
          ...prev,
          `[${data.speaker}]: ${data.text}`
        ]);
      };

      ws.onerror = (e) => {
        console.error("WebSocket error:", e);
        setStatus("Transcription error!");
      };

      websocketRef.current = ws;

      // MediaRecorder setup
      const mediaRecorder = new MediaRecorder(stream, {
  mimeType: "audio/webm"
});
      mediaRecorderRef.current = mediaRecorder;

      // Har 5 second mein audio chunk bhejo
      mediaRecorder.ondataavailable = async (event) => {
        if (
          event.data.size > 0 &&
          ws.readyState === WebSocket.OPEN
        ) {
          const arrayBuffer = await event.data.arrayBuffer();
          ws.send(arrayBuffer);
        }
      };

      // Har 5 second mein chunk banao
      mediaRecorder.start(10000);
      setIsRecording(true);
      setStatus("Recording... Bolo!");

    } catch (error) {
      alert(
        "Microphone access nahi mila! " +
        "Browser mein microphone allow karo."
      );
      console.error(error);
    }
  };

  const stopRecording = () => {
    if (mediaRecorderRef.current) {
      mediaRecorderRef.current.stop();
      mediaRecorderRef.current.stream
        .getTracks()
        .forEach(track => track.stop());
    }
    if (websocketRef.current) {
      setTimeout(() => {
  websocketRef.current?.close();
}, 2000);
    }
    setIsRecording(false);
    setStatus("Recording stopped!");
  };

  return (
    <div className="min-h-screen bg-gray-900 text-white p-8">

      {/* Back Button */}
      <button
        onClick={() => router.push("/dashboard")}
        className="mb-6 text-gray-400 hover:text-white"
      >
        ← Back to Dashboard
      </button>

      <h1 className="text-3xl font-bold mb-2">
        Meeting Room
      </h1>

      {/* Room Info */}
      {roomCode && (
        <div className="bg-gray-800 p-4 rounded-xl mb-6 
                        flex justify-between items-center">
          <div>
            <p className="text-gray-400 text-sm">Room Code</p>
            <p className="text-2xl font-bold text-white">
              {roomCode}
            </p>
          </div>
          {/* Status Badge */}
          <span className={`px-4 py-2 rounded-full font-bold ${
            meetingStatus === "active"
              ? "bg-green-500"
              : meetingStatus === "ended"
              ? "bg-red-500"
              : "bg-yellow-500 text-black"
          }`}>
            {meetingStatus === "active"
              ? "LIVE"
              : meetingStatus === "ended"
              ? "Ended"
              : "Scheduled"}
          </span>
        </div>
      )}

      {/* Control Buttons */}
      <div className="flex gap-4 mb-6 flex-wrap">

        {/* Start Meeting */}
        {meetingId && meetingStatus === "scheduled" && (
          <button
            onClick={startMeeting}
            disabled={loading}
            className="bg-green-600 hover:bg-green-700
                       px-6 py-3 rounded-lg font-bold
                       disabled:opacity-50"
          >
            {loading ? "Starting..." : "Start Meeting"}
          </button>
        )}

        {/* Start Recording */}
        {meetingStatus === "active" && !isRecording && (
          <button
            onClick={startRecording}
            className="bg-red-600 hover:bg-red-700
                       px-6 py-3 rounded-lg font-bold
                       flex items-center gap-2"
          >
            🎤 Start Recording
          </button>
        )}

        {/* Stop Recording */}
        {isRecording && (
          <button
            onClick={stopRecording}
            className="bg-gray-600 hover:bg-gray-700
                       px-6 py-3 rounded-lg font-bold
                       animate-pulse"
          >
            ⏹ Stop Recording
          </button>
        )}

        {/* End Meeting */}
        {meetingId && meetingStatus === "active" && (
          <button
            onClick={endMeeting}
            disabled={loading}
            className="bg-red-800 hover:bg-red-900
                       px-6 py-3 rounded-lg font-bold
                       disabled:opacity-50"
          >
            {loading ? "Ending..." : "End Meeting"}
          </button>
        )}

        {/* Go to Dashboard */}
        <button
          onClick={() => router.push("/dashboard")}
          className="bg-gray-600 hover:bg-gray-700
                     px-6 py-3 rounded-lg font-bold"
        >
          Go to Dashboard
        </button>

      </div>

      {/* Status Message */}
      {status && (
        <div className="bg-blue-900 border border-blue-500 
                        p-3 rounded-lg mb-6">
          <p className="text-blue-300 font-medium">
            {status}
          </p>
        </div>
      )}

      {/* Live Transcript */}
      {transcript.length > 0 && (
        <div className="bg-gray-800 p-6 rounded-xl">
          <h2 className="text-xl font-bold mb-4">
            Live Transcript
          </h2>
          <div className="space-y-2 max-h-64 overflow-y-auto">
            {transcript.map((line, i) => (
              <p
                key={i}
                className="text-gray-300 text-sm 
                           border-l-2 border-blue-500 pl-3"
              >
                {line}
              </p>
            ))}
          </div>

          {/* MOM Generate Button */}
          <button
            onClick={() => router.push(`/mom?meeting_id=${meetingId}`)}
            className="mt-4 bg-blue-600 hover:bg-blue-700
                       px-6 py-3 rounded-lg font-bold w-full"
          >
            Generate MOM from Transcript
          </button>
        </div>
      )}

    </div>
  );
}