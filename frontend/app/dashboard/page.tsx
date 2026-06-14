"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Navbar from "@/components/Navbar";

export default function DashboardPage() {
const router = useRouter();
const [userName, setUserName] = useState("");

useEffect(() => {
const token = localStorage.getItem("token");
const name = localStorage.getItem("userName");

if (!token) {
  router.push("/login");
}

if (name) {
  setUserName(name);
}

}, []);

const createMeeting = async () => {
try {
const token = localStorage.getItem("token");

  if (!token) {
    alert("Please login first!");
    router.push("/login");
    return;
  }

  const response = await fetch(
    "http://localhost:8000/meeting/create",
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({
        title: "New Meeting",
      }),
    }
  );

  const data = await response.json();

  if (response.ok) {
    alert(
      `Meeting Created Successfully! Room Code: ${data.room_code}`
    );

    router.push(
      `/meeting?id=${data.meeting_id}&code=${data.room_code}`
    );
  } else {
    alert(`Error: ${data.detail}`);
  }
} catch (error) {
  console.error(error);
  alert("Meeting creation failed.");
}

};

const joinMeeting = () => {
const input = document.getElementById(
"roomCode"
) as HTMLInputElement;

const code = input?.value?.trim();

if (!code) {
  alert("Please enter a room code!");
  return;
}

router.push(`/meeting?code=${code}`);

};

return ( <div className="min-h-screen bg-gray-100"> <Navbar />

  <div className="p-8">
    <h1 className="text-3xl font-bold mb-2">
      Welcome Back, {userName}!
    </h1>

    <p className="text-gray-500 mb-8">
      Manage your meetings here
    </p>

    <div className="grid grid-cols-1 md:grid-cols-3 gap-6">

      {/* Create Meeting */}
      <div className="bg-white p-6 rounded-xl shadow">
        <h2 className="text-xl font-semibold mb-2">
          New Meeting
        </h2>

        <p className="text-gray-400 mb-4">
          Create and start a new meeting instantly
        </p>

        <button
          onClick={createMeeting}
          className="mt-4 bg-blue-500 hover:bg-blue-600 text-white px-4 py-2 rounded-lg w-full"
        >
          + Create Meeting
        </button>
      </div>

      {/* Past Meetings */}
      <div className="bg-white p-6 rounded-xl shadow">
        <h2 className="text-xl font-semibold mb-2">
          Past Meetings
        </h2>

        <p className="text-gray-400">
          No meetings available yet
        </p>
      </div>

      {/* Quick Join */}
      <div className="bg-white p-6 rounded-xl shadow">
        <h2 className="text-xl font-semibold mb-2">
          Quick Join
        </h2>

        <input
          id="roomCode"
          type="text"
          placeholder="Enter Room Code"
          className="w-full border p-2 rounded-lg mt-2"
        />

        <button
          onClick={joinMeeting}
          className="w-full bg-green-500 hover:bg-green-600 text-white p-2 rounded-lg mt-3"
        >
          Join Now
        </button>
      </div>

    </div>

    {/* Stats Section */}
    <div className="mt-8 bg-white p-6 rounded-xl shadow">
      <h2 className="text-xl font-semibold mb-4">
        Your Statistics
      </h2>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">

        <div className="bg-blue-50 p-4 rounded-lg text-center">
          <p className="text-3xl font-bold text-blue-600">
            0
          </p>
          <p className="text-gray-500">
            Total Meetings
          </p>
        </div>

        <div className="bg-green-50 p-4 rounded-lg text-center">
          <p className="text-3xl font-bold text-green-600">
            0
          </p>
          <p className="text-gray-500">
            Hours Spent
          </p>
        </div>

        <div className="bg-purple-50 p-4 rounded-lg text-center">
          <p className="text-3xl font-bold text-purple-600">
            0
          </p>
          <p className="text-gray-500">
            Recordings
          </p>
        </div>

        <div className="bg-orange-50 p-4 rounded-lg text-center">
          <p className="text-3xl font-bold text-orange-600">
            0
          </p>
          <p className="text-gray-500">
            Participants
          </p>
        </div>

      </div>
    </div>

  </div>
</div>

);
}
