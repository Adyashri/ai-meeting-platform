"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";

export default function RegisterPage() {
const router = useRouter();

const [name, setName] = useState("");
const [email, setEmail] = useState("");
const [password, setPassword] = useState("");
const [loading, setLoading] = useState(false);

const handleRegister = async () => {
if (!name || !email || !password) {
alert("Please fill all fields.");
return;
}

try {
  setLoading(true);

  const response = await fetch(
    "http://localhost:8000/auth/register",
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        name,
        email,
        password,
      }),
    }
  );

  const data = await response.json();

  if (response.ok) {
    alert("Registration Successful ✅");
    router.push("/login");
  } else {
    alert(data.detail || "Registration Failed ❌");
  }
} catch (error: any) {
  console.error(error);
  alert("Error: " + error.message);
} finally {
  setLoading(false);
}

};

return ( <div className="flex min-h-screen items-center justify-center bg-gray-100"> <div className="bg-white p-8 rounded-lg shadow-md w-96"> <h1 className="text-2xl font-bold text-center mb-6">
Create Account </h1>

    <input
      type="text"
      placeholder="Full Name"
      className="w-full border p-2 rounded mb-4"
      value={name}
      onChange={(e) => setName(e.target.value)}
    />

    <input
      type="email"
      placeholder="Email Address"
      className="w-full border p-2 rounded mb-4"
      value={email}
      onChange={(e) => setEmail(e.target.value)}
    />

    <input
      type="password"
      placeholder="Password"
      className="w-full border p-2 rounded mb-4"
      value={password}
      onChange={(e) => setPassword(e.target.value)}
    />

    <button
      onClick={handleRegister}
      disabled={loading}
      className="w-full bg-green-600 hover:bg-green-700 text-white p-2 rounded disabled:bg-gray-400"
    >
      {loading ? "Creating Account..." : "Register"}
    </button>

    <p className="text-center mt-4 text-gray-500">
      Already have an account?{" "}
      <Link href="/login" className="text-blue-500 hover:underline">
        Login
      </Link>
    </p>
  </div>
</div>

);
}
