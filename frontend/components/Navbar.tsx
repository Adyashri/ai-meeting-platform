"use client";

import { useRouter } from "next/navigation";

export default function Navbar() {
  const router = useRouter();

  const handleLogout = () => {
    localStorage.clear();
    router.replace("/login");
  };

  return (
    <nav className="bg-blue-600 text-white p-4 flex justify-between items-center">
      <h1 className="text-xl font-bold">AI Meeting Platform</h1>

      <div className="flex gap-4 items-center">
        <button
          onClick={() => router.push("/dashboard")}
          className="hover:underline"
        >
          Dashboard
        </button>

        <button
          onClick={handleLogout}
          className="bg-white text-blue-600 px-4 py-1 rounded font-semibold"
        >
          Logout
        </button>
      </div>
    </nav>
  );
}