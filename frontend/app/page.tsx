"use client";
import { useEffect } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";

export default function Home() {
  const router = useRouter();
  useEffect(() => {
    const token = localStorage.getItem("token");
    router.replace(token ? "/admin/surveys" : "/auth");
  }, [router]);
  return (
    <div className="min-h-screen flex items-center justify-center text-center text-gray-400">
      <div>
        <p>Redirecting...</p>
        <p className="mt-2 text-sm">If you are a participant, open your survey link (e.g. <code>/survey/SHARECODE</code>).</p>
        <p className="mt-1 text-sm">Researchers: <Link className="text-blue-600" href="/auth">Sign in</Link></p>
      </div>
    </div>
  );
}
