"use client";

import { Suspense, useEffect } from "react";
import { useRouter, useSearchParams } from "next/navigation";

function LoginSuccessContent() {
  const nav    = useRouter();
  const params = useSearchParams();

  useEffect(() => {
    const token  = params.get("token");
    const name   = params.get("name");
    const email  = params.get("email");
    const userId = params.get("user_id");
    const error  = params.get("error");

    if (error || !token) {
      nav.replace("/login?error=google_failed");
      return;
    }

    localStorage.setItem("token",     token);
    localStorage.setItem("userName",  name    || "");
    localStorage.setItem("userEmail", email   || "");
    localStorage.setItem("userId",    userId  || "");
    nav.replace("/dashboard");
  }, [params, nav]);

  return (
    <div className="min-h-screen flex items-center justify-center"
         style={{ background: "#0f1117" }}>
      <div className="text-center">
        <div className="w-8 h-8 border-2 border-t-transparent rounded-full animate-spin mx-auto mb-3"
             style={{ borderColor: "#6b7fff", borderTopColor: "transparent" }} />
        <p className="text-white font-medium">Signing you in with Google…</p>
        <p className="text-sm mt-1" style={{ color: "#8892a4" }}>Please wait</p>
      </div>
    </div>
  );
}

export default function LoginSuccess() {
  return (
    <Suspense fallback={
      <div className="min-h-screen flex items-center justify-center"
           style={{ background: "#0f1117" }}>
        <div className="w-8 h-8 border-2 rounded-full animate-spin"
             style={{ borderColor: "#6b7fff", borderTopColor: "transparent" }} />
      </div>
    }>
      <LoginSuccessContent />
    </Suspense>
  );
}