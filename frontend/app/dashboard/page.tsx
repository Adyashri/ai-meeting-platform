"use client";
import { useRouter } from "next/navigation";
import Navbar from "@/components/Navbar";

export default function DashboardPage() {
  const router = useRouter();
  return (
    <div className="min-h-screen bg-gray-100">
      <Navbar />
      <div className="p-8">
        <h1 className="text-3xl font-bold mb-2">Welcome Back! 👋</h1>
        <p className="text-gray-500 mb-8">Manage your meetings here</p>
        <div className="grid grid-cols-3 gap-6">
          <div className="bg-white p-6 rounded-xl shadow">
            <h2 className="text-xl font-semibold mb-2">📅 Upcoming Meetings</h2>
            <p className="text-gray-400">No meetings scheduled</p>
            <button onClick={() => router.push("/meeting")}
              className="mt-4 bg-blue-500 text-white px-4 py-2 rounded-lg w-full">
              + Create Meeting
            </button>
          </div>
          <div className="bg-white p-6 rounded-xl shadow">
            <h2 className="text-xl font-semibold mb-2">🕐 Past Meetings</h2>
            <p className="text-gray-400">No past meetings</p>
          </div>
          <div className="bg-white p-6 rounded-xl shadow">
            <h2 className="text-xl font-semibold mb-2">⚡ Quick Join</h2>
            <input type="text" placeholder="Enter meeting ID"
              className="w-full border p-2 rounded-lg mt-2"/>
            <button onClick={() => router.push("/meeting")}
              className="w-full bg-green-500 text-white p-2 rounded-lg mt-3">
              Join Now
            </button>
          </div>
        </div>
        <div className="mt-8 bg-white p-6 rounded-xl shadow">
          <h2 className="text-xl font-semibold mb-4">📊 Your Stats</h2>
          <div className="grid grid-cols-4 gap-4">
            <div className="bg-blue-50 p-4 rounded-lg text-center">
              <p className="text-3xl font-bold text-blue-600">0</p>
              <p className="text-gray-500">Total Meetings</p>
            </div>
            <div className="bg-green-50 p-4 rounded-lg text-center">
              <p className="text-3xl font-bold text-green-600">0</p>
              <p className="text-gray-500">Hours Spent</p>
            </div>
            <div className="bg-purple-50 p-4 rounded-lg text-center">
              <p className="text-3xl font-bold text-purple-600">0</p>
              <p className="text-gray-500">Recordings</p>
            </div>
            <div className="bg-orange-50 p-4 rounded-lg text-center">
              <p className="text-3xl font-bold text-orange-600">0</p>
              <p className="text-gray-500">Participants</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}