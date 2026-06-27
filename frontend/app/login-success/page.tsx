"use client";

import { useEffect } from "react";
import { useRouter, useSearchParams } from "next/navigation";

export default function LoginSuccessPage() {
  const router = useRouter();
  const searchParams = useSearchParams();

  useEffect(() => {
    const token = searchParams.get("token");
    const name = searchParams.get("name");
    const userId = searchParams.get("user_id");

    if (!token) {
      alert("Google login failed: token not found");
      router.push("/login");
      return;
    }

    localStorage.setItem("token", token);

    if (name) {
      localStorage.setItem("userName", decodeURIComponent(name));
    }

    if (userId) {
      localStorage.setItem("userId", decodeURIComponent(userId));
    }

    router.replace("/dashboard");
  }, [router, searchParams]);

  return (
    <div className="min-h-screen flex items-center justify-center text-lg">
      Google login ho raha hai...
    </div>
  );
}