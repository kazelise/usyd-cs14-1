"use client";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";

export default function AdminLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const [authed, setAuthed] = useState(false);

  useEffect(() => {
    const token = localStorage.getItem("token");
    if (!token) {
      router.replace("/auth");
    } else {
      setAuthed(true);
    }
  }, [router]);

  function logout() {
    localStorage.removeItem("token");
    router.push("/auth");
  }

  if (!authed) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <p className="text-gray-400">Checking authentication...</p>
      </div>
    );
  }

  return (
    <div className="min-h-screen">
      <nav className="bg-white border-b px-6 py-3 flex items-center justify-between">
        <Link href="/admin/surveys" className="text-lg font-bold text-blue-600">
          CS14 Survey Platform
        </Link>
        <button onClick={logout} className="text-sm text-gray-500 hover:text-red-500">
          Logout
        </button>
      </nav>
      <main className="max-w-5xl mx-auto p-6">{children}</main>
    </div>
  );
}
