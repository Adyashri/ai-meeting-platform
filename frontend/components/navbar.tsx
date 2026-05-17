"use client";
import { useRouter } from "next/navigation";

export default function Navbar() {
  const router = useRouter();
  return (
    <nav className="bg-blue-600 text-white px-6 py-4 flex justify-between items-center shadow-lg">
      <h1 className="text-xl font-bold cursor-pointer" onClick={() => router.push("/")}>
        🎥 AI Meeting Platform
      </h1>
      <div className="flex gap-4 items-center">
        <button onClick={() => router.push("/dashboard")}
          className="hover:underline">Dashboard</button>
        <button onClick={() => router.push("/meeting")}
          className="hover:underline">Join Meeting</button>
        <button onClick={() => router.push("/login")}
          className="bg-white text-blue-600 px-4 py-1 rounded font-semibold">
          Logout
        </button>
      </div>
    </nav>
  );
}