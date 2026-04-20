"use client";
import { useEffect } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { useLocale } from "@/components/locale-provider";

export default function Home() {
  const router = useRouter();
  const { locale } = useLocale();
  const text =
    locale === "zh"
      ? {
          redirecting: "正在跳转...",
          participantHint: "如果你是参与者，请打开你的问卷链接，例如",
          researcher: "研究者：",
          signIn: "登录",
        }
      : {
          redirecting: "Redirecting...",
          participantHint: "If you are a participant, open your survey link (e.g.",
          researcher: "Researchers:",
          signIn: "Sign in",
        };
  useEffect(() => {
    const token = localStorage.getItem("token");
    router.replace(token ? "/admin/surveys" : "/auth");
  }, [router]);
  return (
    <div className="min-h-screen flex items-center justify-center text-center text-gray-400">
      <div>
        <p>{text.redirecting}</p>
        <p className="mt-2 text-sm">{text.participantHint} <code>/survey/SHARECODE</code>).</p>
        <p className="mt-1 text-sm">{text.researcher} <Link className="text-blue-600" href="/auth">{text.signIn}</Link></p>
      </div>
    </div>
  );
}
