"use client";

// Role-aware landing after auth: users go to the claim chatbot, admins to the review console.
import { useRouter } from "next/navigation";
import { useEffect } from "react";
import { useAuth } from "../../lib/auth";

export default function Dashboard() {
  const { user, role, loading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (loading) return;
    if (!user) router.replace("/signin");
    else router.replace(role === "admin" ? "/admin" : "/chat");
  }, [loading, user, role, router]);

  return (
    <div style={{ minHeight: "100vh", display: "grid", placeItems: "center" }}>
      <span className="muted mono">Taking you to your workspace…</span>
    </div>
  );
}
