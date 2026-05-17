"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";

export default function RegisterPage() {
  const router = useRouter();
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  const handleRegister = () => {
    if (name && email && password) {
      router.push("/dashboard");
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-gray-100">
      <div className="bg-white p-8 rounded-lg shadow-md w-96">
        <h1 className="text-2xl font-bold mb-6 text-center">Register</h1>
        <input type="text" placeholder="Full Name"
          className="w-full border p-2 rounded mb-4"
          onChange={(e) => setName(e.target.value)}/>
        <input type="email" placeholder="Email"
          className="w-full border p-2 rounded mb-4"
          onChange={(e) => setEmail(e.target.value)}/>
        <input type="password" placeholder="Password"
          className="w-full border p-2 rounded mb-4"
          onChange={(e) => setPassword(e.target.value)}/>
        <button onClick={handleRegister}
          className="w-full bg-green-500 text-white p-2 rounded">
          Register
        </button>
        <p className="text-center mt-4 text-gray-500">
          Already have account? <a href="/login" className="text-blue-500">Login</a>
        </p>
      </div>
    </div>
  );
}