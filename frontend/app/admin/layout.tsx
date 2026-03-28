"use client";
import { useRouter } from "next/navigation";
import Link from "next/link";

export default function AdminLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter();

  function logout() {
    localStorage.removeItem("token");
    router.push("/auth");
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
