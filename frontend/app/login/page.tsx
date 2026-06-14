"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

export default function LoginPage() {
const router = useRouter();

const [email, setEmail] = useState("");
const [password, setPassword] = useState("");
const [loading, setLoading] = useState(false);

const handleLogin = async () => {
if (!email || !password) {
alert("Please enter your email and password.");
return;
}

setLoading(true);

try {
  const formData = new URLSearchParams();
  formData.append("username", email);
  formData.append("password", password);

  const response = await fetch(
    "http://localhost:8000/auth/login",
    {
      method: "POST",
      headers: {
        "Content-Type":
          "application/x-www-form-urlencoded",
      },
      body: formData,
    }
  );

  const data = await response.json();

  console.log("LOGIN RESPONSE:", data);

  if (response.ok) {
    localStorage.setItem(
      "token",
      data.access_token
    );

    localStorage.setItem(
      "userName",
      data.user.name
    );

    localStorage.setItem(
      "userId",
      data.user.id
    );

    alert("Login Successful ✅");

    router.push("/dashboard");
  } else {
    alert(data.detail || "Login Failed ❌");
  }
} catch (error) {
  console.error("LOGIN ERROR:", error);

  alert(
    "Unable to connect to server. Please make sure the backend is running."
  );
} finally {
  setLoading(false);
}

};

return ( <div
   className="min-h-screen bg-gray-900 flex items-center justify-center"
 > <div
     className="bg-white p-8 rounded-2xl shadow-xl w-full max-w-md"
   > <h1
       className="text-3xl font-bold text-center mb-2 text-gray-800"
     >
AI Meeting Platform </h1>

    <p className="text-center text-gray-500 mb-8">
      Sign in to continue
    </p>

    {/* Email */}
    <div className="mb-4">
      <label
        className="block text-gray-700 font-medium mb-1"
      >
        Email Address
      </label>

      <input
        type="email"
        placeholder="Enter your email address"
        value={email}
        onChange={(e) =>
          setEmail(e.target.value)
        }
        className="w-full border border-gray-300 p-3 rounded-lg focus:outline-none focus:border-blue-500"
      />
    </div>

    {/* Password */}
    <div className="mb-6">
      <label
        className="block text-gray-700 font-medium mb-1"
      >
        Password
      </label>

      <input
        type="password"
        placeholder="Enter your password"
        value={password}
        onChange={(e) =>
          setPassword(e.target.value)
        }
        onKeyDown={(e) => {
          if (e.key === "Enter") {
            handleLogin();
          }
        }}
        className="w-full border border-gray-300 p-3 rounded-lg focus:outline-none focus:border-blue-500"
      />
    </div>

    {/* Login Button */}
    <button
      onClick={handleLogin}
      disabled={loading}
      className="w-full bg-blue-600 hover:bg-blue-700 text-white font-bold py-3 rounded-lg transition disabled:opacity-50"
    >
      {loading
        ? "Signing In..."
        : "Login"}
    </button>

    {/* Register Link */}
    <p className="text-center text-gray-500 mt-4">
      Don't have an account?{" "}
      <span
        onClick={() =>
          router.push("/register")
        }
        className="text-blue-600 font-semibold cursor-pointer hover:underline"
      >
        Create Account
      </span>
    </p>
  </div>
</div>

);
}
