"use client";

import { useState, useEffect } from "react";
import Navbar from "@/components/Navbar";

export default function ProfilePage() {
  const [editing, setEditing] = useState(false);

  const [name, setName] = useState("");
  const [email, setEmail] = useState("");

  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchUser = async () => {
      try {
        const token = localStorage.getItem("token");

        const response = await fetch("http://localhost:8000/user/me", {
          method: "GET",
          headers: {
            Authorization: `Bearer ${token}`,
            "Content-Type": "application/json",
          },
        });

        const data = await response.json();

        setName(data.name);
        setEmail(data.email);
      } catch (error) {
        console.error("Profile fetch error:", error);
      } finally {
        setLoading(false);
      }
    };

    fetchUser();
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        Loading profile...
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-100">
      <Navbar />

      <div className="p-8 max-w-2xl mx-auto">
        <div className="bg-white p-8 rounded-xl shadow text-center">

          {/* PROFILE ICON */}
          <div className="w-24 h-24 bg-blue-500 rounded-full mx-auto mb-4 flex items-center justify-center">
            <p className="text-white text-4xl">👤</p>
          </div>

          {/* EDIT MODE */}
          {editing ? (
            <div className="text-left">
              <input
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                className="w-full border p-2 rounded-lg mb-3"
                placeholder="Full Name"
              />

              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full border p-2 rounded-lg mb-3"
                placeholder="Email"
              />

              <button
                onClick={() => setEditing(false)}
                className="w-full bg-green-500 text-white px-6 py-2 rounded-lg"
              >
                Save Profile ✅
              </button>
            </div>
          ) : (
            <>
              {/* DISPLAY MODE */}
              <h1 className="text-2xl font-bold">{name}</h1>
              <p className="text-gray-500 mb-6">{email}</p>

              <div className="grid grid-cols-2 gap-4 text-left">

                <div className="bg-gray-50 p-4 rounded-lg">
                  <p className="text-gray-500 text-sm">Full Name</p>
                  <p className="font-semibold">{name}</p>
                </div>

                <div className="bg-gray-50 p-4 rounded-lg">
                  <p className="text-gray-500 text-sm">Email</p>
                  <p className="font-semibold">{email}</p>
                </div>

                <div className="bg-gray-50 p-4 rounded-lg">
                  <p className="text-gray-500 text-sm">Role</p>
                  <p className="font-semibold">User</p>
                </div>

                <div className="bg-gray-50 p-4 rounded-lg">
                  <p className="text-gray-500 text-sm">Status</p>
                  <p className="font-semibold text-green-600">Active</p>
                </div>

              </div>

              <button
                onClick={() => setEditing(true)}
                className="mt-6 bg-blue-500 text-white px-6 py-2 rounded-lg w-full"
              >
                Edit Profile ✏️
              </button>
            </>
          )}

        </div>
      </div>
    </div>
  );
}