"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useParams, useSearchParams } from "next/navigation";
import { api } from "@/lib/api";
import { useLocale } from "@/components/locale-provider";
import { isLocale, t, type Locale } from "@/lib/i18n";
import { CheckCircleIcon, GlobeIcon, LinkIcon, SurveyIcon, UsersIcon } from "@/components/icons";
import { CalibrationExperience } from "@/components/calibration-experience";
import { ExternalPostImage } from "@/components/external-post-image";
import { GazeTrackingPip } from "@/components/gaze-tracking-pip";
import { useGazeTracker } from "./useGazeTracker";

type PlatformStyle = "x" | "facebook" | "instagram" | "xiaohongshu";
type PlatformUiStyle = "twitter" | "facebook" | "instagram" | "xiaohongshu" | "truth_social" | "bluesky" | "douyin";
type FeedSkin = "x" | "facebook" | "instagram" | "xiaohongshu" | "truth_social" | "bluesky" | "douyin";

const PLATFORM_FEED_STYLES: Record<
  FeedSkin,
  {
      name: string;
      pageClass: string;
      pageMaxClass: string;
      contentGridClass: string;
      leftAsideClass: string;
      mainClass: string;
      introClass: string;
      feedClass: string;
      rightAsideClass: string;
      accentTextClass: string;
      accentBgClass: string;
      progressClass: string;
      cardClass: string;
    headerClass: string;
    avatarClass: string;
    badgeClass: string;
    imageWrapClass: string;
    imageClass: string;
    moreInfoButtonClass: string;
    engagementClass: string;
      actionGridClass: string;
      actionButtonClass: string;
      actionButtonDividerClass: string;
      activeActionClass: string;
      bodyClass: string;
      titleClass: string;
      descriptionClass: string;
      commentCardClass: string;
      participantCommentClass: string;
    }
> = {
  x: {
      name: "X",
      pageClass: "bg-[linear-gradient(180deg,#f8fafc_0%,#eef2f7_100%)]",
      pageMaxClass: "mx-auto max-w-[1280px] px-4 py-6 lg:px-6 lg:py-8",
      contentGridClass: "grid gap-6 xl:grid-cols-[240px_minmax(0,640px)_300px] xl:justify-center",
      leftAsideClass: "space-y-6 xl:sticky xl:top-6 xl:self-start",
      mainClass: "min-w-0 space-y-4",
      introClass: "surface-panel-soft flex flex-col gap-3 px-6 py-5 md:flex-row md:items-center md:justify-between",
      feedClass: "space-y-4",
      rightAsideClass: "space-y-6 xl:sticky xl:top-6 xl:self-start",
      accentTextClass: "text-slate-900",
      accentBgClass: "bg-slate-900",
      progressClass: "bg-slate-900",
      cardClass: "overflow-hidden rounded-[18px] border border-slate-200 bg-white shadow-sm",
      headerClass: "border-b border-slate-200 bg-white px-6 py-4",
      avatarClass: "flex h-10 w-10 items-center justify-center rounded-full bg-slate-900 text-[13px] font-semibold text-white",
      badgeClass: "inline-flex rounded-full bg-slate-100 px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-600",
      imageWrapClass: "border-b border-slate-200 bg-slate-100",
      imageClass: "h-72 w-full object-cover",
      moreInfoButtonClass: "mt-4 inline-flex max-w-full items-center gap-2 rounded-full border border-slate-200 bg-white px-3 py-2 text-[13px] font-semibold text-slate-700 transition hover:border-slate-900/30 hover:bg-slate-100",
      engagementClass: "flex flex-wrap items-center gap-6 border-t border-slate-200 bg-white px-6 py-4 text-[13px] text-slate-500",
      actionGridClass: "grid border-t border-slate-200 text-[13px] md:grid-cols-3",
      actionButtonClass: "border-slate-200 px-4 py-4 font-semibold text-slate-600 transition hover:bg-slate-50",
      actionButtonDividerClass: "border-t md:border-l md:border-t-0",
      activeActionClass: "bg-slate-900 text-white hover:bg-slate-800",
      bodyClass: "px-6 py-5",
      titleClass: "mt-3 text-[19px] font-semibold leading-7 tracking-[-0.03em] text-[#163047]",
      descriptionClass: "mt-2 text-[14px] leading-7 text-slate-600",
      commentCardClass: "rounded-[18px] border border-slate-200 bg-slate-50 px-4 py-4",
      participantCommentClass: "rounded-[18px] border border-slate-300 bg-white px-4 py-4",
    },
  facebook: {
      name: "Facebook",
      pageClass: "bg-[linear-gradient(180deg,#f3f7ff_0%,#e9eef7_100%)]",
      pageMaxClass: "mx-auto max-w-[1320px] px-4 py-6 lg:px-6 lg:py-8",
      contentGridClass: "grid gap-6 xl:grid-cols-[260px_minmax(0,680px)_300px] xl:justify-center",
      leftAsideClass: "space-y-6 xl:sticky xl:top-6 xl:self-start",
      mainClass: "min-w-0 space-y-6",
      introClass: "surface-panel-soft flex flex-col gap-3 px-6 py-5 md:flex-row md:items-center md:justify-between",
      feedClass: "space-y-5",
      rightAsideClass: "space-y-6 xl:sticky xl:top-6 xl:self-start",
      accentTextClass: "text-[#1877f2]",
      accentBgClass: "bg-[#1877f2]",
      progressClass: "bg-[#1877f2]",
    cardClass: "overflow-hidden rounded-[18px] border border-blue-100 bg-white shadow-[0_16px_42px_rgba(24,119,242,0.10)]",
    headerClass: "border-b border-blue-50 bg-white px-6 py-4",
    avatarClass: "flex h-11 w-11 items-center justify-center rounded-full bg-[#1877f2] text-[13px] font-semibold text-white",
    badgeClass: "inline-flex rounded-full bg-blue-50 px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.18em] text-[#1877f2]",
    imageWrapClass: "border-b border-blue-50 bg-blue-50",
    imageClass: "h-72 w-full object-cover",
    moreInfoButtonClass: "mt-4 inline-flex max-w-full items-center gap-2 rounded-[12px] border border-blue-100 bg-blue-50 px-3 py-2 text-[13px] font-semibold text-[#1877f2] transition hover:bg-blue-100",
      engagementClass: "flex flex-wrap items-center gap-6 border-t border-blue-50 bg-blue-50/50 px-6 py-4 text-[13px] text-slate-600",
      actionGridClass: "grid border-t border-blue-50 text-[13px] md:grid-cols-3",
      actionButtonClass: "border-blue-50 px-4 py-4 font-semibold text-slate-600 transition hover:bg-blue-50",
      actionButtonDividerClass: "border-t md:border-l md:border-t-0",
      activeActionClass: "bg-[#1877f2] text-white hover:bg-[#1668d8]",
      bodyClass: "px-6 py-5",
      titleClass: "mt-4 text-[22px] font-semibold leading-8 tracking-[-0.03em] text-[#163047]",
      descriptionClass: "mt-3 text-[14px] leading-7 text-slate-600",
      commentCardClass: "rounded-[18px] border border-blue-100 bg-blue-50/60 px-4 py-4",
      participantCommentClass: "rounded-[18px] border border-blue-200 bg-white px-4 py-4",
    },
  instagram: {
      name: "Instagram",
      pageClass: "bg-[linear-gradient(180deg,#fff7fb_0%,#f5f5f7_100%)]",
      pageMaxClass: "mx-auto max-w-[1120px] px-4 py-6 lg:px-6 lg:py-8",
      contentGridClass: "grid justify-center gap-6",
      leftAsideClass: "hidden",
      mainClass: "w-full max-w-[640px] space-y-6",
      introClass: "hidden",
      feedClass: "space-y-8",
      rightAsideClass: "mx-auto w-full max-w-[640px] space-y-4",
      accentTextClass: "text-[#c13584]",
      accentBgClass: "bg-[#c13584]",
      progressClass: "bg-[linear-gradient(90deg,#f58529_0%,#dd2a7b_48%,#515bd4_100%)]",
      cardClass: "overflow-hidden rounded-[6px] border border-slate-200 bg-white shadow-[0_12px_32px_rgba(193,53,132,0.08)]",
      headerClass: "border-b border-slate-100 bg-white px-6 py-4",
      avatarClass: "flex h-11 w-11 items-center justify-center rounded-full bg-[linear-gradient(135deg,#f58529,#dd2a7b,#515bd4)] text-[13px] font-semibold text-white",
      badgeClass: "inline-flex rounded-[8px] bg-pink-50 px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.18em] text-[#c13584]",
      imageWrapClass: "bg-black",
      imageClass: "aspect-[4/5] w-full object-cover",
      moreInfoButtonClass: "mt-4 inline-flex max-w-full items-center gap-2 rounded-[10px] border border-pink-100 bg-pink-50 px-3 py-2 text-[13px] font-semibold text-[#c13584] transition hover:bg-pink-100",
      engagementClass: "flex flex-wrap items-center gap-6 border-t border-slate-100 bg-white px-6 py-4 text-[13px] text-slate-600",
      actionGridClass: "grid border-t border-slate-100 text-[13px] md:grid-cols-3",
      actionButtonClass: "border-slate-100 px-4 py-4 font-semibold text-slate-700 transition hover:bg-pink-50",
      actionButtonDividerClass: "border-t md:border-l md:border-t-0",
      activeActionClass: "bg-[#c13584] text-white hover:bg-[#a62b70]",
      bodyClass: "px-4 py-4",
      titleClass: "mt-3 text-[16px] font-semibold leading-6 text-[#262626]",
      descriptionClass: "mt-2 text-[14px] leading-6 text-slate-700",
      commentCardClass: "rounded-[12px] border border-slate-200 bg-slate-50 px-4 py-4",
      participantCommentClass: "rounded-[12px] border border-pink-200 bg-pink-50/40 px-4 py-4",
    },
  xiaohongshu: {
      name: "Xiaohongshu",
      pageClass: "bg-[linear-gradient(180deg,#fff8f8_0%,#f7f2f0_100%)]",
      pageMaxClass: "mx-auto max-w-[1380px] px-4 py-5 lg:px-7 lg:py-8",
      contentGridClass: "grid gap-5",
      leftAsideClass: "hidden",
      mainClass: "min-w-0",
      introClass: "hidden",
      feedClass: "columns-1 gap-4 sm:columns-2 xl:columns-3 [column-fill:_balance]",
      rightAsideClass: "mx-auto w-full max-w-[760px] space-y-4",
      accentTextClass: "text-[#ff2442]",
      accentBgClass: "bg-[#ff2442]",
      progressClass: "bg-[#ff2442]",
      cardClass: "mb-4 inline-block w-full break-inside-avoid overflow-hidden rounded-[18px] border border-rose-100 bg-white shadow-[0_10px_28px_rgba(255,36,66,0.08)]",
      headerClass: "hidden",
      avatarClass: "flex h-10 w-10 items-center justify-center rounded-full bg-[#ff2442] text-[13px] font-semibold text-white",
      badgeClass: "inline-flex rounded-full bg-rose-50 px-2.5 py-1 text-[10px] font-semibold uppercase tracking-[0.14em] text-[#ff2442]",
      imageWrapClass: "bg-rose-50",
      imageClass: "w-full object-cover",
      moreInfoButtonClass: "mt-3 inline-flex max-w-full items-center gap-1.5 rounded-full border border-rose-100 bg-rose-50 px-3 py-1.5 text-[12px] font-semibold text-[#ff2442] transition hover:bg-rose-100",
      engagementClass: "flex flex-wrap items-center gap-3 px-4 pb-3 pt-1 text-[12px] text-slate-500",
      actionGridClass: "grid grid-cols-3 gap-2 px-3 pb-3 text-[12px]",
      actionButtonClass: "rounded-full px-3 py-2 font-semibold text-slate-600 transition hover:bg-rose-50",
      actionButtonDividerClass: "border-0",
      activeActionClass: "bg-[#ff2442] text-white hover:bg-[#e01f39]",
      bodyClass: "px-4 pb-4 pt-3",
      titleClass: "mt-3 text-[15px] font-semibold leading-6 text-[#1f2933]",
      descriptionClass: "mt-2 max-h-[72px] overflow-hidden text-[13px] leading-6 text-slate-600",
      commentCardClass: "rounded-[14px] border border-rose-100 bg-rose-50/50 px-3 py-3",
      participantCommentClass: "rounded-[14px] border border-rose-200 bg-white px-3 py-3",
    },
  truth_social: {
      name: "Truth Social-style",
      pageClass: "bg-[linear-gradient(180deg,#f4f6fb_0%,#e4e9f2_100%)]",
      pageMaxClass: "mx-auto max-w-[1240px] px-4 py-6 lg:px-6 lg:py-8",
      contentGridClass: "grid gap-6 xl:grid-cols-[240px_minmax(0,640px)_300px] xl:justify-center",
      leftAsideClass: "space-y-6 xl:sticky xl:top-6 xl:self-start",
      mainClass: "min-w-0 space-y-4",
      introClass: "surface-panel-soft flex flex-col gap-3 px-6 py-5 md:flex-row md:items-center md:justify-between",
      feedClass: "space-y-4",
      rightAsideClass: "space-y-6 xl:sticky xl:top-6 xl:self-start",
      accentTextClass: "text-[#b22234]",
      accentBgClass: "bg-[#1a2a4f]",
      progressClass: "bg-[#b22234]",
      cardClass: "overflow-hidden rounded-[10px] border-2 border-[#1a2a4f] bg-white shadow-[0_14px_36px_rgba(26,42,79,0.18)]",
      headerClass: "border-b-2 border-[#b22234] bg-[#1a2a4f] px-6 py-4 text-white",
      avatarClass: "flex h-11 w-11 items-center justify-center rounded-full border-2 border-white bg-[#b22234] text-[13px] font-bold uppercase text-white",
      badgeClass: "inline-flex rounded-[4px] bg-[#1a2a4f] px-3 py-1 text-[11px] font-bold uppercase tracking-[0.2em] text-white",
      imageWrapClass: "border-b border-slate-200 bg-slate-100",
      imageClass: "h-72 w-full object-cover",
      moreInfoButtonClass: "mt-4 inline-flex max-w-full items-center gap-2 rounded-[6px] border-2 border-[#1a2a4f] bg-white px-3 py-2 text-[13px] font-bold uppercase tracking-[0.08em] text-[#1a2a4f] transition hover:bg-[#1a2a4f] hover:text-white",
      engagementClass: "flex flex-wrap items-center gap-6 border-t-2 border-[#1a2a4f]/15 bg-[#f4f6fb] px-6 py-4 text-[13px] font-semibold text-[#1a2a4f]",
      actionGridClass: "grid border-t-2 border-[#1a2a4f]/15 text-[13px] md:grid-cols-3",
      actionButtonClass: "border-[#1a2a4f]/15 px-4 py-4 font-bold uppercase tracking-[0.08em] text-[#1a2a4f] transition hover:bg-[#1a2a4f]/5",
      actionButtonDividerClass: "border-t md:border-l md:border-t-0",
      activeActionClass: "bg-[#b22234] text-white hover:bg-[#9a1a2a]",
      bodyClass: "px-6 py-5",
      titleClass: "mt-3 text-[20px] font-bold leading-7 tracking-[-0.02em] text-[#1a2a4f]",
      descriptionClass: "mt-2 text-[14px] leading-7 text-slate-700",
      commentCardClass: "rounded-[8px] border border-[#1a2a4f]/15 bg-[#f4f6fb] px-4 py-4",
      participantCommentClass: "rounded-[8px] border-2 border-[#b22234]/60 bg-white px-4 py-4",
    },
  bluesky: {
      name: "Bluesky-style",
      pageClass: "bg-[linear-gradient(180deg,#eef6ff_0%,#dbeafe_100%)]",
      pageMaxClass: "mx-auto max-w-[1200px] px-4 py-6 lg:px-6 lg:py-8",
      contentGridClass: "grid gap-6 xl:grid-cols-[240px_minmax(0,620px)_300px] xl:justify-center",
      leftAsideClass: "space-y-6 xl:sticky xl:top-6 xl:self-start",
      mainClass: "min-w-0 space-y-4",
      introClass: "surface-panel-soft flex flex-col gap-3 px-6 py-5 md:flex-row md:items-center md:justify-between",
      feedClass: "space-y-4",
      rightAsideClass: "space-y-6 xl:sticky xl:top-6 xl:self-start",
      accentTextClass: "text-[#0085ff]",
      accentBgClass: "bg-[#0085ff]",
      progressClass: "bg-[linear-gradient(90deg,#0085ff_0%,#33b1ff_100%)]",
      cardClass: "overflow-hidden rounded-[20px] border border-[#cfe3ff] bg-white shadow-[0_12px_34px_rgba(0,133,255,0.12)]",
      headerClass: "border-b border-[#e0eeff] bg-white px-6 py-4",
      avatarClass: "flex h-11 w-11 items-center justify-center rounded-full bg-[linear-gradient(135deg,#0085ff,#33b1ff)] text-[13px] font-semibold text-white",
      badgeClass: "inline-flex rounded-full bg-[#e6f1ff] px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.18em] text-[#0066c8]",
      imageWrapClass: "border-b border-[#e0eeff] bg-[#eef6ff]",
      imageClass: "h-72 w-full object-cover",
      moreInfoButtonClass: "mt-4 inline-flex max-w-full items-center gap-2 rounded-full border border-[#cfe3ff] bg-[#eef6ff] px-3 py-2 text-[13px] font-semibold text-[#0066c8] transition hover:bg-[#dbeafe]",
      engagementClass: "flex flex-wrap items-center gap-6 border-t border-[#e0eeff] bg-[#f6fbff] px-6 py-4 text-[13px] text-slate-600",
      actionGridClass: "grid border-t border-[#e0eeff] text-[13px] md:grid-cols-3",
      actionButtonClass: "border-[#e0eeff] px-4 py-4 font-semibold text-[#0066c8] transition hover:bg-[#eef6ff]",
      actionButtonDividerClass: "border-t md:border-l md:border-t-0",
      activeActionClass: "bg-[#0085ff] text-white hover:bg-[#0070d6]",
      bodyClass: "px-6 py-5",
      titleClass: "mt-3 text-[19px] font-semibold leading-7 tracking-[-0.02em] text-[#0c1e3a]",
      descriptionClass: "mt-2 text-[14px] leading-7 text-slate-600",
      commentCardClass: "rounded-[16px] border border-[#cfe3ff] bg-[#f6fbff] px-4 py-4",
      participantCommentClass: "rounded-[16px] border border-[#0085ff]/40 bg-white px-4 py-4",
    },
  douyin: {
      name: "Douyin / TikTok",
      pageClass: "bg-[#080b10]",
      pageMaxClass: "mx-auto max-w-[1120px] px-4 py-5 lg:px-6 lg:py-7",
      contentGridClass: "grid justify-center gap-5 lg:grid-cols-[minmax(0,460px)_minmax(280px,340px)] lg:items-start",
      leftAsideClass: "hidden",
      mainClass: "min-w-0 space-y-5",
      introClass: "hidden",
      feedClass: "space-y-6",
      rightAsideClass: "w-full space-y-4 lg:sticky lg:top-6 lg:self-start [&_.surface-panel]:border-white/10 [&_.surface-panel]:bg-white/95 [&_.surface-panel-soft]:border-white/10 [&_.surface-panel-soft]:bg-white/95",
      accentTextClass: "text-[#fe2c55]",
      accentBgClass: "bg-[#fe2c55]",
      progressClass: "bg-[linear-gradient(90deg,#25f4ee_0%,#fe2c55_100%)]",
      cardClass: "overflow-hidden rounded-[28px] border border-white/10 bg-[#111820] text-white shadow-[0_24px_80px_rgba(0,0,0,0.42)]",
      headerClass: "hidden",
      avatarClass: "flex h-11 w-11 items-center justify-center rounded-full border border-white/20 bg-[#fe2c55] text-[13px] font-bold text-white",
      badgeClass: "inline-flex rounded-full bg-white/10 px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.18em] text-white/80",
      imageWrapClass: "bg-black",
      imageClass: "aspect-[9/16] w-full object-cover",
      moreInfoButtonClass: "mt-4 inline-flex max-w-full items-center gap-2 rounded-full border border-white/15 bg-white/10 px-3 py-2 text-[13px] font-semibold text-white transition hover:bg-white/15",
      engagementClass: "flex flex-wrap items-center gap-4 border-t border-white/10 bg-black/25 px-5 py-4 text-[13px] text-white/70",
      actionGridClass: "grid grid-cols-3 gap-2 border-t border-white/10 bg-black/20 px-3 py-3 text-[12px]",
      actionButtonClass: "rounded-full px-3 py-2 font-semibold text-white/80 transition hover:bg-white/10",
      actionButtonDividerClass: "border-0",
      activeActionClass: "bg-[#fe2c55] text-white hover:bg-[#e3264d]",
      bodyClass: "px-5 py-5",
      titleClass: "mt-4 text-[20px] font-semibold leading-7 text-white",
      descriptionClass: "mt-2 text-[14px] leading-7 text-white/70",
      commentCardClass: "rounded-[18px] border border-white/10 bg-white/10 px-4 py-4",
      participantCommentClass: "rounded-[18px] border border-[#25f4ee]/50 bg-[#25f4ee]/10 px-4 py-4",
    },
};

function getPlatformFeedStyle(style?: string | null) {
    return PLATFORM_FEED_STYLES[(style as FeedSkin) || "x"] ?? PLATFORM_FEED_STYLES.x;
}

function platformUiStyleToFeedSkin(style?: PlatformUiStyle | null): FeedSkin | null {
  if (!style) return null;
  if (style === "twitter") return "x";
  return style;
}

function getPostImageClass(skin: FeedSkin, baseClass: string, index: number) {
    if (skin !== "xiaohongshu") return baseClass;
    const ratios = ["aspect-[3/4]", "aspect-square", "aspect-[4/5]", "aspect-[5/4]"];
    return `${baseClass} ${ratios[index % ratios.length]}`;
}

function hostnameFromUrl(url: string) {
  try {
    return new URL(url).hostname || "Unknown";
  } catch {
    return "Unknown";
  }
}

/** Terminal label after a share is recorded; matches platform verb where possible */
function getPlatformShareRecordedLabel(skin: FeedSkin, locale: Locale): string {
  if (skin === "x") {
    if (locale === "zh") return "已转发";
    if (locale === "ar") return "تمّت إعادة النشر";
    return "Reposted";
  }
  if (skin === "bluesky") {
    if (locale === "zh") return "已转发";
    if (locale === "ar") return "تمّت إعادة النشر";
    return "Reposted";
  }
  if (skin === "truth_social") {
    if (locale === "zh") return "已ReTruth";
    if (locale === "ar") return "تمّ تأكيد ReTruth";
    return "ReTruthed";
  }
  if (skin === "xiaohongshu") {
    if (locale === "zh") return "已收藏";
    if (locale === "ar") return "تم الحفظ";
    return "Collected";
  }
  if (skin === "douyin") {
    if (locale === "zh") return "已分享";
    if (locale === "ar") return "تمّت المشاركة";
    return "Shared";
  }
  return t(locale, "shareRecordedButton");
}

function getPlatformActionLabels(skin: FeedSkin, locale: Locale) {
  if (skin === "x") {
    return locale === "zh"
      ? { like: "喜欢", liked: "已喜欢", comment: "回复", share: "转发" }
      : { like: "Like", liked: "Liked", comment: "Reply", share: "Repost" };
  }
  if (skin === "xiaohongshu") {
    return locale === "zh"
      ? { like: "赞", liked: "已赞", comment: "评论", share: "收藏" }
      : { like: "Like", liked: "Liked", comment: "Comment", share: "Collect" };
  }
  if (skin === "truth_social") {
    return locale === "zh"
      ? { like: "喜欢", liked: "已喜欢", comment: "回复", share: "转发" }
      : { like: "Like", liked: "Liked", comment: "Reply", share: "ReTruth" };
  }
  if (skin === "bluesky") {
    return locale === "zh"
      ? { like: "喜欢", liked: "已喜欢", comment: "回复", share: "转发" }
      : { like: "Like", liked: "Liked", comment: "Reply", share: "Repost" };
  }
  if (skin === "douyin") {
    return locale === "zh"
      ? { like: "喜欢", liked: "已喜欢", comment: "评论", share: "转发" }
      : { like: "Heart", liked: "Hearted", comment: "Comment", share: "Share" };
  }
  return {
    like: t(locale, "like"),
    liked: t(locale, "liked"),
    comment: t(locale, "comment"),
    share: t(locale, "share"),
  };
}

function PlatformFeedChrome({
  skin,
  platformName,
  locale,
}: {
  skin: FeedSkin;
  platformName: string;
  locale: Locale;
}) {
  if (skin === "instagram") {
    const labels = locale === "zh" ? ["账号", "帖子", "收藏", "洞察"] : ["Profile", "Posts", "Saved", "Insights"];
    return (
      <div className="rounded-[6px] border border-slate-200 bg-white px-5 py-4">
        <div className="flex items-center justify-between gap-4">
          <p className="text-[18px] font-semibold text-[#262626]">Instagram</p>
          <div className="flex gap-3">
            {labels.map((label, index) => (
              <span key={label} className={`h-10 w-10 rounded-full border-2 ${index === 0 ? "border-[#dd2a7b]" : "border-slate-200"} bg-slate-50`} title={label} />
            ))}
          </div>
        </div>
      </div>
    );
  }

  if (skin === "xiaohongshu") {
    const labels = locale === "zh" ? ["关注", "发现", "图文笔记", "生活方式"] : ["Following", "Discover", "Notes", "Lifestyle"];
    return (
      <div className="sticky top-0 z-10 -mx-1 flex gap-2 overflow-x-auto bg-[#fff8f8]/90 px-1 py-2 backdrop-blur">
        {labels.map((label, index) => (
          <span key={label} className={`shrink-0 rounded-full px-4 py-2 text-[13px] font-semibold ${index === 1 ? "bg-[#ff2442] text-white" : "bg-white text-slate-600"}`}>
            {label}
          </span>
        ))}
      </div>
    );
  }

  if (skin === "truth_social") {
    return (
      <div className="overflow-hidden rounded-[10px] border-2 border-[#1a2a4f] bg-white">
        <div className="bg-[#1a2a4f] px-5 py-3 text-[12px] font-bold uppercase tracking-[0.18em] text-white">
          {platformName} feed
        </div>
        <div className="grid grid-cols-3 divide-x divide-[#1a2a4f]/15 text-center text-[13px] font-bold uppercase tracking-[0.08em] text-[#1a2a4f]">
          <span className="py-3">Following</span>
          <span className="py-3">Truths</span>
          <span className="py-3">Replies</span>
        </div>
      </div>
    );
  }

  if (skin === "bluesky") {
    return (
      <div className="rounded-[22px] border border-[#cfe3ff] bg-white/90 p-2 shadow-[0_12px_34px_rgba(0,133,255,0.10)] backdrop-blur">
        <div className="grid grid-cols-2 rounded-[18px] bg-[#eef6ff] p-1 text-center text-[13px] font-semibold text-[#0066c8]">
          <span className="rounded-[14px] bg-white px-4 py-2 shadow-sm">Following</span>
          <span className="px-4 py-2">Discover</span>
        </div>
      </div>
    );
  }

  if (skin === "douyin") {
    return (
      <div className="rounded-[26px] border border-white/10 bg-white/5 px-5 py-4 text-white shadow-[0_20px_60px_rgba(0,0,0,0.28)]">
        <div className="flex items-center justify-between gap-4">
          <p className="text-[12px] font-semibold uppercase tracking-[0.22em] text-[#25f4ee]">Vertical feed</p>
          <div className="flex gap-2 text-[12px] font-semibold">
            <span className="rounded-full bg-white px-3 py-1.5 text-black">Following</span>
            <span className="rounded-full bg-white/10 px-3 py-1.5 text-white/70">For You</span>
          </div>
        </div>
        <p className="mt-3 text-[13px] leading-6 text-white/60">
          {locale === "zh" ? "短视频式深色信息流，用于展示更沉浸的社交平台刺激。" : "Dark short-form feed treatment for immersive social stimuli."}
        </p>
      </div>
    );
  }

  return null;
}

interface Comment {
  id: number;
  author_name: string;
  text: string;
}

interface Question {
  id: number;
  survey_id: number;
  post_id: number | null;
  order: number;
  question_type: string; // text / single_choice / multiple_choice / likert / rating
  text: string;
  config: { min?: number; max?: number; min_label?: string; max_label?: string; options?: string[] } | null;
}

interface Post {
  id: number;
  original_url: string;
  fetched_title: string | null;
  fetched_image_url: string | null;
  fetched_description: string | null;
  fetched_source: string | null;
  display_title: string | null;
  display_image_url: string | null;
  display_description: string | null;
  source_label: string | null;
  more_info_label?: string;
  display_likes: number;
  display_comments_count: number;
  display_shares: number;
  show_likes: boolean;
  show_comments: boolean;
  show_shares: boolean;
  comments: Comment[];
  questions: Question[];
}

interface SurveySession {
  response_id: number;
  participant_token: string;
  survey_id: number;
  assigned_group: number;
  platform_style: PlatformStyle;
  platform_ui_style?: PlatformUiStyle;
  calibration_required: boolean;
  calibration_points: number;
  calibration_completed: boolean;
  gaze_tracking_enabled: boolean;
  gaze_interval_ms: number;
  click_tracking_enabled: boolean;
  posts: Post[];
  questions: Question[];
}

interface ParticipantComment {
  id: number;
  post_id: number;
  text: string;
}

export default function SurveyParticipantPage() {
  const params = useParams();
  const shareCode = params.shareCode as string;
  const search = useSearchParams();
  const { locale, setLocale } = useLocale();
  const requestedLocale = search.get("lang");
  const isPreviewSession = search.get("preview") === "1";
  const previewGroupParam = search.get("group");
  const previewAssignedGroup = previewGroupParam ? Number(previewGroupParam) : null;
  const previewScope = Number.isFinite(previewAssignedGroup) ? previewAssignedGroup : "auto";
  // Use "en" fallback, not the live locale context: locale-provider hydrates
  // from localStorage via useEffect, so using `locale` here would make
  // initialLocale change post-mount and re-trigger the session init effect.
  const initialLocale: Locale = isLocale(requestedLocale) ? requestedLocale : "en";

  const [session, setSession] = useState<SurveySession | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [completed, setCompleted] = useState(false);
  const [actionError, setActionError] = useState("");
  const [calibrationDone, setCalibrationDone] = useState(false);
  const [likedPosts, setLikedPosts] = useState<Set<number>>(new Set());
  const [clickedPosts, setClickedPosts] = useState<Set<number>>(new Set());
  const [commentInputs, setCommentInputs] = useState<Record<number, string>>({});
  const [showCommentInput, setShowCommentInput] = useState<number | null>(null);
  const [participantComments, setParticipantComments] = useState<Record<number, ParticipantComment[]>>({});
  // Question answers: { [questionId]: answer }
  const [questionAnswers, setQuestionAnswers] = useState<Record<number, { text?: string; value?: number; choices?: string[] }>>({});
  const [submittedQuestions, setSubmittedQuestions] = useState<Set<number>>(new Set());
  /** Once a share is recorded successfully for a post, UI stays in the terminal "Shared" state (+1 display cap). */
  const [shareSessionRecorded, setShareSessionRecorded] = useState<Record<number, boolean>>({});
  const [shareSubmittingId, setShareSubmittingId] = useState<number | null>(null);
  const [toastMessage, setToastMessage] = useState<string | null>(null);

  const [completing, setCompleting] = useState(false);
  const [likeSubmittingPosts, setLikeSubmittingPosts] = useState<Set<number>>(new Set());

  const clickBuffer = useRef<any[]>([]);
  const likeInFlightRef = useRef<Set<number>>(new Set());
  const initializedSessionRef = useRef<string | null>(null);
  const gazePipVideoRef = useRef<HTMLVideoElement | null>(null);

  const handleTrackedClick = useCallback((e: MouseEvent) => {
    const target = e.target as HTMLElement | null;
    if (!target) return;
    if (target.closest("[data-gaze-pip]")) return;

    let targetElement = "other";

    if (target.closest("[data-track='more_info']")) targetElement = "more_info";
    else if (target.closest("[data-track='image']")) targetElement = "image";
    else if (target.closest("[data-track='headline']")) targetElement = "headline";
    else if (target.closest("[data-track='like']")) targetElement = "like_button";
    else if (target.closest("[data-track='comment']")) targetElement = "comment_button";
    else if (target.closest("[data-track='share']")) targetElement = "share_count";

    const postEl = target.closest("[data-post-id]");
    const postId = postEl ? Number(postEl.getAttribute("data-post-id")) : null;

    clickBuffer.current.push({
      post_id: postId,
      timestamp_ms: Date.now(),
      screen_x: e.clientX,
      screen_y: e.clientY,
      target_element: targetElement,
    });
  }, []);

  const flushClicks = useCallback(async (responseId: number, participantToken: string) => {
    if (clickBuffer.current.length === 0) return;
    const batch = [...clickBuffer.current];
    clickBuffer.current = [];
    try {
      await api.recordClicks({ response_id: responseId, participant_token: participantToken, data: batch });
    } catch {
      clickBuffer.current = [...batch, ...clickBuffer.current];
    }
  }, []);

  // Gaze tracking — runs continuously during survey after calibration
  const {
    flush: flushGaze,
    snapshot: gazeSnapshot,
    getSummary: getGazeSummary,
  } = useGazeTracker({
    responseId: session?.response_id ?? 0,
    participantToken: session?.participant_token ?? "",
    intervalMs: session?.gaze_interval_ms ?? 1000,
    enabled: !isPreviewSession && calibrationDone && !!session?.gaze_tracking_enabled,
    pipVideoRef: gazePipVideoRef,
  });

  useEffect(() => {
    if (!toastMessage) return;
    const id = window.setTimeout(() => setToastMessage(null), 2400);
    return () => window.clearTimeout(id);
  }, [toastMessage]);

  useEffect(() => {
    setLocale(initialLocale);
  }, [initialLocale, setLocale]);

  useEffect(() => {
    const sessionScope = `${shareCode}:${isPreviewSession ? `preview:${previewScope}:${initialLocale}` : `live:${initialLocale}`}`;
    if (initializedSessionRef.current === sessionScope) return;
    initializedSessionRef.current = sessionScope;

    async function init() {
      setLoading(true);
      setError("");
      try {
        // Resume the same response (and A/B group) across tab closes by sending
        // back the participant_token cached on first visit. Backend ignores
        // tokens that don't match an in_progress response for this survey.
        const tokenStorageKey = isPreviewSession
          ? `pt:${shareCode}:preview:${previewScope}:${initialLocale}`
          : `pt:${shareCode}:${initialLocale}`;
        const completionStorageKey = isPreviewSession
          ? `completed:${shareCode}:preview:${previewScope}:${initialLocale}`
          : `completed:${shareCode}:${initialLocale}`;
        if (localStorage.getItem(completionStorageKey)) {
          setCompleted(true);
          return;
        }
        const cachedToken = localStorage.getItem(tokenStorageKey) || undefined;
        const result = await api.startSurvey(shareCode, {
          language: initialLocale,
          screen_width: window.innerWidth,
          screen_height: window.innerHeight,
          user_agent: navigator.userAgent,
          participant_token: cachedToken,
          is_preview: isPreviewSession,
          preview_assigned_group:
            isPreviewSession && Number.isFinite(previewAssignedGroup) ? previewAssignedGroup as number : undefined,
        });
        setSession(result);
        setClickedPosts(new Set());
        setShareSessionRecorded({});
        localStorage.setItem(tokenStorageKey, result.participant_token);
        // Resume hint from backend: a prior calibration on this response was
        // already completed, so skip the calibration UI for the user. If the
        // researcher disabled calibration, raw gaze/click tracking can start
        // directly without showing the calibration screen.
        if (result.is_preview || result.calibration_completed || !result.calibration_required) {
          setCalibrationDone(true);
        }

        const submittedQuestionsKey = `answers:${result.response_id}:${result.participant_token}`;
        const savedSubmittedQuestions = JSON.parse(localStorage.getItem(submittedQuestionsKey) || "[]");
        setSubmittedQuestions(
          new Set<number>(Array.isArray(savedSubmittedQuestions) ? savedSubmittedQuestions : []),
        );

        try {
          const state = await api.getResponseState(result.response_id, result.participant_token);
          setLikedPosts(new Set<number>(state.liked_post_ids || []));
          setParticipantComments(state.comments_by_post || {});
        } catch {}
      } catch (err: any) {
        const message = err.message || t(initialLocale, "surveyNotFound");
        if (
          isPreviewSession &&
          /auth|login|unauthorized|forbidden|not authenticated/i.test(message)
        ) {
          setError(
            initialLocale === "zh"
              ? "预览需要先以研究者身份登录，再从管理端打开预览链接。"
              : "Preview requires a logged-in researcher session. Sign in from the admin area, then reopen this preview link.",
          );
        } else {
          setError(message);
        }
      } finally {
        setLoading(false);
      }
    }

    init();
  }, [initialLocale, isPreviewSession, previewAssignedGroup, previewScope, shareCode]);

  useEffect(() => {
    if (!session?.click_tracking_enabled || completed) return;

    document.addEventListener("click", handleTrackedClick);
    const flushInterval = setInterval(() => {
      void flushClicks(session.response_id, session.participant_token);
    }, 10000);

    return () => {
      document.removeEventListener("click", handleTrackedClick);
      clearInterval(flushInterval);
      void flushClicks(session.response_id, session.participant_token);
    };
  }, [
    completed,
    flushClicks,
    handleTrackedClick,
    session?.click_tracking_enabled,
    session?.participant_token,
    session?.response_id,
  ]);

  function rememberSubmittedQuestion(questionId: number) {
    setSubmittedQuestions((prev) => {
      const next = new Set([...prev, questionId]);
      if (session) {
        localStorage.setItem(
          `answers:${session.response_id}:${session.participant_token}`,
          JSON.stringify([...next]),
        );
      }
      return next;
    });
  }

  async function handleLike(postId: number) {
    if (!session) return;
    if (likeInFlightRef.current.has(postId)) return;
    likeInFlightRef.current.add(postId);
    setLikeSubmittingPosts((prev) => new Set([...prev, postId]));
    setActionError("");

    setLikedPosts((prev) => {
      const next = new Set(prev);
      if (next.has(postId)) next.delete(postId);
      else next.add(postId);
      return next;
    });

    try {
      await api.toggleLike(session.response_id, postId, session.participant_token);
    } catch (err: any) {
      setLikedPosts((prev) => {
        const next = new Set(prev);
        if (next.has(postId)) next.delete(postId);
        else next.add(postId);
        return next;
      });
      setActionError(err.message || t(locale, "networkRequestFailed"));
    } finally {
      likeInFlightRef.current.delete(postId);
      setLikeSubmittingPosts((prev) => {
        const next = new Set(prev);
        next.delete(postId);
        return next;
      });
    }
  }

  async function handleComment(postId: number) {
    if (!session) return;
    const text = commentInputs[postId];
    if (!text?.trim()) return;
    setActionError("");

    try {
      const created = await api.createParticipantComment(session.response_id, {
        post_id: postId,
        text,
        participant_token: session.participant_token,
      });
      setParticipantComments((prev) => ({
        ...prev,
        [postId]: [...(prev[postId] || []), created],
      }));
      setCommentInputs((prev) => ({ ...prev, [postId]: "" }));
      setShowCommentInput(null);
    } catch (err: any) {
      setActionError(err.message || t(locale, "networkRequestFailed"));
    }
  }

  async function handleClickPost(postId: number) {
    if (!session) return;
    setActionError("");
    try {
      await api.recordInteraction(session.response_id, {
        post_id: postId,
        action_type: "click",
        participant_token: session.participant_token,
      });
      setClickedPosts((prev) => new Set([...prev, postId]));
    } catch (err: any) {
      setActionError(err.message || t(locale, "networkRequestFailed"));
    }
  }

  async function handleShareAction(postId: number) {
    if (!session || shareSubmittingId !== null) return;
    if (shareSessionRecorded[postId]) return;
    setShareSubmittingId(postId);
    setActionError("");
    try {
      await api.recordInteraction(session.response_id, {
        post_id: postId,
        action_type: "share",
        participant_token: session.participant_token,
      });
      setShareSessionRecorded((prev) => ({ ...prev, [postId]: true }));
      setToastMessage(t(locale, "shareRecordedToast"));
    } catch (err: any) {
      setActionError(err.message || t(locale, "networkRequestFailed"));
    } finally {
      setShareSubmittingId(null);
    }
  }

  async function handleComplete() {
    if (!session || completing) return;
    setCompleting(true);
    setActionError("");
    try {
      await flushClicks(session.response_id, session.participant_token);
      await flushGaze();
      const attentionSummary =
        !isPreviewSession && session.gaze_tracking_enabled ? getGazeSummary() : null;
      await api.completeSurvey(
        session.response_id,
        session.participant_token,
        attentionSummary,
      );
      // Drop the cached token so a fresh visit to the same share link starts
      // a new response from the start screen, while a refresh of this completed
      // page keeps showing completion instead of opening an orphan response.
      localStorage.setItem(
        isPreviewSession
          ? `completed:${shareCode}:preview:${previewScope}:${initialLocale}`
          : `completed:${shareCode}:${initialLocale}`,
        new Date().toISOString(),
      );
      localStorage.removeItem(
        isPreviewSession
          ? `pt:${shareCode}:preview:${previewScope}:${initialLocale}`
          : `pt:${shareCode}:${initialLocale}`,
      );
      localStorage.removeItem(`answers:${session.response_id}:${session.participant_token}`);
      setCompleted(true);
    } catch (err: any) {
      const raw = err.message || "";
      if (/calibration must be completed/i.test(raw)) {
        setActionError(
          locale === "zh"
            ? "请先完成摄像头校准后再提交。"
            : "Complete webcam calibration before submitting.",
        );
      } else if (/post interaction|required answer/i.test(raw)) {
        setActionError(completionHint);
      } else if (/missing_required_answers/i.test(raw)) {
        setActionError(
          locale === "zh" ? "仍有必答题未提交。" : "Some required question answers are still missing.",
        );
      } else {
        setActionError(raw || t(locale, "networkRequestFailed"));
      }
    } finally {
      setCompleting(false);
    }
  }

  if (loading) {
    return <div className="flex min-h-screen items-center justify-center text-sm uppercase tracking-[0.24em] text-slate-400">{t(locale, "loadingSurvey")}</div>;
  }

  if (error) {
    return <div className="flex min-h-screen items-center justify-center px-6 text-center text-red-500">{error}</div>;
  }

  if (completed) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-[linear-gradient(180deg,#f7fafc_0%,#eef3f8_100%)] px-6">
        <div className="surface-panel max-w-xl px-8 py-10 text-center">
          <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-[22px] bg-[#0f3146] text-white">
            <CheckCircleIcon className="h-7 w-7" />
          </div>
          <h1 className="mt-6 text-4xl font-semibold tracking-[-0.05em] text-[#163047]">{t(locale, "thankYou")}</h1>
          <p className="mt-3 text-sm leading-7 text-slate-500">{t(locale, "recorded")}</p>
          <p className="mt-2 text-xs text-slate-400">{t(locale, "completionDetails")}</p>
        </div>
      </div>
    );
  }

  if (!session) return null;

  // Show calibration if required and not yet completed
  if (session.calibration_required && !calibrationDone && !isPreviewSession) {
    return (
      <CalibrationExperience
        responseId={session.response_id}
        participantToken={session.participant_token}
        expectedPoints={session.calibration_points}
        onComplete={(_result) => setCalibrationDone(true)}
      />
    );
  }

  const totalPosts = session.posts.length;
  const requiredQuestionIds = [
    ...(session.questions || []),
    ...session.posts.flatMap((post) => post.questions || []),
  ].map((question) => question.id);
  const answeredQuestionCount = requiredQuestionIds.filter((questionId) =>
    submittedQuestions.has(questionId),
  ).length;
  const commentedPostIds = Object.keys(participantComments)
    .filter((key) => (participantComments[Number(key)] || []).length > 0)
    .map(Number);
  const sharedPostIds = Object.entries(shareSessionRecorded)
    .filter(([, recorded]) => recorded)
    .map(([postId]) => Number(postId));
  const interactedPostIds = new Set([
    ...likedPosts,
    ...clickedPosts,
    ...commentedPostIds,
    ...sharedPostIds,
  ]);
  const activityUnits = totalPosts + requiredQuestionIds.length;
  const completedUnits = Math.min(totalPosts, interactedPostIds.size) + answeredQuestionCount;
  const progressValue =
    activityUnits === 0 ? 100 : Math.min(100, Math.round((completedUnits / activityUnits) * 100));
  const questionsComplete = answeredQuestionCount === requiredQuestionIds.length;
  const engagementComplete =
    requiredQuestionIds.length > 0 ? questionsComplete : totalPosts === 0 || interactedPostIds.size > 0;
  const calibrationSatisfied =
    isPreviewSession || !session.calibration_required || calibrationDone;
  const canCompleteSurvey = isPreviewSession || (calibrationSatisfied && engagementComplete);
  const completionHint = !calibrationSatisfied
    ? locale === "zh"
      ? "请先完成摄像头校准。"
      : "Complete webcam calibration before submitting."
    : locale === "zh"
      ? requiredQuestionIds.length > 0
        ? "请先提交所有题目答案。"
        : "请先至少与一条帖子互动（点赞、评论、点击或分享）。"
      : requiredQuestionIds.length > 0
        ? "Submit every question answer before completing."
        : "Interact with at least one post (like, comment, click, or share) before completing.";
  const researchNotes = [
    session.click_tracking_enabled ? t(locale, "noteClicks") : null,
    session.gaze_tracking_enabled ? t(locale, "noteGaze") : null,
    session.calibration_required ? t(locale, "noteCalibration") : null,
  ].filter(Boolean) as string[];
  const interactionSummary =
    locale === "zh"
      ? `已完成 ${completedUnits} / ${activityUnits} 个必要动作`
      : `${completedUnits} / ${activityUnits} required actions complete`;
  const recordedAcrossSummary =
    locale === "zh"
      ? `${Math.min(totalPosts, interactedPostIds.size)} 条帖子有交互，${answeredQuestionCount} 道题已提交`
      : `${Math.min(totalPosts, interactedPostIds.size)} posts interacted with, ${answeredQuestionCount} answers submitted`;
  const feedSkin: FeedSkin = platformUiStyleToFeedSkin(session.platform_ui_style)
    || ((session.platform_style || "x") as FeedSkin);
  const platform = getPlatformFeedStyle(feedSkin);
  const platformActionLabels = getPlatformActionLabels(feedSkin, locale);
  const platformShareRecordedLabel = getPlatformShareRecordedLabel(feedSkin, locale);

  return (
    <div className={`min-h-screen ${platform.pageClass}`}>
      {!isPreviewSession && calibrationDone && session.gaze_tracking_enabled && (
        <GazeTrackingPip snapshot={gazeSnapshot} locale={locale} videoRef={gazePipVideoRef} />
      )}
      {toastMessage && (
        <div
          role="status"
          className="fixed left-1/2 top-[max(1rem,env(safe-area-inset-top))] z-[70] -translate-x-1/2 rounded-full border border-slate-200 bg-[#163047] px-5 py-2.5 text-center text-[13px] font-medium text-white shadow-lg"
        >
          {toastMessage}
        </div>
      )}
      {isPreviewSession && (
        <div className="border-b border-amber-200 bg-amber-50 px-4 py-2 text-center text-[12px] font-semibold uppercase tracking-[0.18em] text-amber-800">
          Preview test session · excluded from analytics exports by default
        </div>
      )}
      <div className="border-b border-slate-200 bg-white/85 backdrop-blur">
        <div className="mx-auto flex max-w-[1560px] flex-col gap-4 px-4 py-4 lg:px-6">
          <div className="flex flex-col gap-4 xl:flex-row xl:items-center xl:justify-between">
            <div>
              <p className={`text-[11px] font-semibold uppercase tracking-[0.22em] ${platform.accentTextClass}`}>{t(locale, "surveySession")}</p>
              <h1 className="mt-2 text-[28px] font-semibold tracking-[-0.05em] text-[#163047]">{t(locale, "participantResponseExperience")}</h1>
              <p className="mt-1 text-[14px] leading-7 text-slate-500">{t(locale, "participantResponseCopy")}</p>
            </div>

            <div className="flex flex-wrap items-center gap-3">
              <div className="rounded-full border border-slate-200 bg-slate-50 px-4 py-2 text-[13px] text-slate-600">
                {t(locale, "assignedGroup")} {session.assigned_group}
              </div>
              <div className="rounded-full border border-slate-200 bg-white px-4 py-2 text-[13px] text-slate-600">
                {platform.name} feed
              </div>
              <div className="flex items-center gap-3 rounded-full border border-slate-200 bg-slate-50 px-4 py-2">
                <GlobeIcon className="h-4 w-4 text-slate-500" aria-hidden />
                <select
                  aria-label={t(locale, "language")}
                  className="bg-transparent text-sm text-slate-500 outline-none disabled:cursor-default disabled:opacity-60"
                  value={locale}
                  onChange={(e) => {
                    const next = e.target.value as Locale;
                    const params = new URLSearchParams(Array.from(search.entries()));
                    params.set("lang", next);
                    window.location.assign(`/survey/${shareCode}?${params.toString()}`);
                  }}
                >
                  <option value="en">English</option>
                  <option value="zh">中文</option>
                  <option value="ar">العربية</option>
                </select>
              </div>
            </div>
          </div>

          <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_220px] xl:items-center">
            <div>
              <div className="mb-2 flex items-center justify-between text-[12px] font-medium text-slate-500">
                <span>{t(locale, "surveyProgress")}</span>
                <span>{progressValue}%</span>
              </div>
              <div className="h-3 overflow-hidden rounded-full bg-slate-200">
                <div
                  className={`h-full rounded-full transition-all ${platform.progressClass}`}
                  style={{ width: `${progressValue}%` }}
                />
              </div>
            </div>
            <div className="text-[13px] text-slate-500 xl:text-right">
              {interactionSummary}
            </div>
          </div>
        </div>
      </div>

      <div className={platform.pageMaxClass}>
        <div className={platform.contentGridClass}>
          <aside className={platform.leftAsideClass}>
            <div className="surface-panel-soft px-6 py-6">
              <div className={`flex h-12 w-12 items-center justify-center rounded-[16px] text-white ${platform.accentBgClass}`}>
                <SurveyIcon className="h-5 w-5" />
              </div>
              <p className={`section-kicker mt-6 ${platform.accentTextClass}`}>{t(locale, "surveyContext")}</p>
              <h2 className="section-title mt-3 md:text-[24px]">{t(locale, "participantFeed")}</h2>
              <p className="mt-4 text-[14px] leading-7 text-slate-500">{t(locale, "participantFeedCopy")}</p>

              <div className="mt-4 space-y-2">
                {calibrationDone && session.gaze_tracking_enabled && (
                  <div className="flex items-center gap-2 rounded-lg bg-emerald-50 px-3 py-2 text-xs text-emerald-700">
                    <span className="h-2 w-2 animate-pulse rounded-full bg-emerald-500" />
                    {t(locale, "gazeTrackingActive")}
                  </div>
                )}
                {session.click_tracking_enabled && (
                  <div className="flex items-center gap-2 rounded-lg bg-cyan-50 px-3 py-2 text-xs text-cyan-700">
                    <span className="h-2 w-2 animate-pulse rounded-full bg-cyan-500" />
                    {t(locale, "clickTrackingActive")}
                  </div>
                )}
                {calibrationDone && (
                  <div className="flex items-center gap-2 rounded-lg bg-slate-100 px-3 py-2 text-xs text-slate-600">
                    <CheckCircleIcon className="h-3 w-3" />
                    {t(locale, "calibrationCompleted")}
                  </div>
                )}
              </div>
            </div>

            <div className="surface-panel-soft px-6 py-6">
              <p className={`section-kicker ${platform.accentTextClass}`}>{t(locale, "sessionSnapshot")}</p>
              <div className="mt-5 space-y-4 text-[14px] leading-7 text-slate-500">
                <p>{t(locale, "assignedGroup")}: <span className="font-medium text-[#163047]">{session.assigned_group}</span></p>
                <p>{t(locale, "clickTracking")}: <span className="font-medium text-[#163047]">{session.click_tracking_enabled ? t(locale, "on") : t(locale, "off")}</span></p>
                <p>{t(locale, "gazeTracking")}: <span className="font-medium text-[#163047]">{session.gaze_tracking_enabled ? t(locale, "on") : t(locale, "off")}</span></p>
                <p>{t(locale, "calibration")}: <span className="font-medium text-[#163047]">{session.calibration_required ? t(locale, "required") : t(locale, "notRequired")}</span></p>
              </div>
            </div>
          </aside>

          <main className={platform.mainClass}>
            <div className={platform.introClass}>
              <div>
                <p className={`section-kicker ${platform.accentTextClass}`}>{t(locale, "studyInstructions")}</p>
                <p className="mt-2 text-[14px] leading-7 text-slate-500">{t(locale, "studyInstructionsCopy")}</p>
              </div>
              <div className="rounded-full border border-slate-200 bg-slate-50 px-4 py-2 text-[13px] text-slate-600">
                {totalPosts} {t(locale, "totalPostsInSurvey")}
              </div>
            </div>

            <PlatformFeedChrome skin={feedSkin} platformName={platform.name} locale={locale} />

            {session.questions && session.questions.length > 0 && (
              <div className="surface-panel-soft space-y-4 px-5 py-5">
                <p className={`text-[11px] font-semibold uppercase tracking-[0.22em] ${platform.accentTextClass}`}>{t(locale, "questionBlock")}</p>
                {session.questions
                  .sort((a, b) => a.order - b.order)
                  .map((q) => {
                    const answered = submittedQuestions.has(q.id);
                    const answer = questionAnswers[q.id] || {};
                    return (
                      <div key={q.id} className={`rounded-[18px] border p-4 ${answered ? "border-emerald-200 bg-emerald-50/60" : "border-slate-200 bg-white"}`}>
                        <p className="text-sm font-semibold text-[#163047]">{q.text}</p>
                        {(q.question_type === "free_text" || q.question_type === "text") && (
                          <textarea
                            className="mt-3 w-full rounded-[14px] border border-slate-200 px-3 py-2 text-sm focus:border-[#00a7a0] focus:outline-none focus:ring-4 focus:ring-[#00a7a0]/10"
                            rows={2}
                            placeholder={t(locale, "typeYourAnswer")}
                            disabled={answered}
                            value={answer.text || ""}
                            onChange={(e) => setQuestionAnswers((prev) => ({ ...prev, [q.id]: { ...prev[q.id], text: e.target.value } }))}
                          />
                        )}
                        {(q.question_type === "likert" || q.question_type === "rating") && q.config && (
                          <div className="mt-3">
                            <div className="mb-1 flex items-center justify-between text-xs text-slate-500">
                              <span>{q.config.min_label || "Strongly Disagree"}</span>
                              <span>{q.config.max_label || "Strongly Agree"}</span>
                            </div>
                            <div className="flex gap-2">
                              {Array.from({ length: (q.config.max ?? 5) - (q.config.min ?? 1) + 1 }, (_, i) => {
                                const val = (q.config!.min ?? 1) + i;
                                const selected = answer.value === val;
                                return (
                                  <button
                                    key={val}
                                    disabled={answered}
                                    onClick={() => setQuestionAnswers((prev) => ({ ...prev, [q.id]: { value: val } }))}
                                    className={`flex-1 rounded-[12px] border py-2 text-sm font-medium transition ${
                                      selected ? "border-[#00a7a0] bg-[#00a7a0] text-white" : "border-slate-200 bg-white text-slate-600 hover:bg-slate-50"
                                    } ${answered ? "opacity-60" : ""}`}
                                  >
                                    {val}
                                  </button>
                                );
                              })}
                            </div>
                          </div>
                        )}
                        {(q.question_type === "multiple_choice" || q.question_type === "single_choice") && q.config?.options && (
                          <div className="mt-3 space-y-2">
                            {q.config.options.map((opt) => {
                              const selected = q.question_type === "single_choice"
                                ? (answer.choices || [])[0] === opt
                                : (answer.choices || []).includes(opt);
                              return (
                                <button
                                  key={opt}
                                  disabled={answered}
                                  onClick={() => {
                                    setQuestionAnswers((prev) => {
                                      if (q.question_type === "single_choice") {
                                        return { ...prev, [q.id]: { choices: [opt], text: opt } };
                                      }
                                      const current = prev[q.id]?.choices || [];
                                      const next = selected ? current.filter((c) => c !== opt) : [...current, opt];
                                      return { ...prev, [q.id]: { choices: next } };
                                    });
                                  }}
                                  className={`block w-full rounded-[12px] border px-3 py-2 text-left text-sm transition ${
                                    selected ? "border-[#00a7a0] bg-[#effcfb] text-[#00847f]" : "border-slate-200 bg-white text-slate-600 hover:bg-slate-50"
                                  } ${answered ? "opacity-60" : ""}`}
                                >
                                  {opt}
                                </button>
                              );
                            })}
                          </div>
                        )}
                        {!answered && (answer.text || (answer.value !== undefined && answer.value !== null) || (answer.choices && answer.choices.length > 0)) && (
                          <button
                            className="primary-button mt-3 px-4 py-2 text-xs"
                            onClick={async () => {
                              if (!session) return;
                              try {
                                setActionError("");
                                await api.submitQuestionResponse(session.response_id, q.id, {
                                  question_id: q.id,
                                  participant_token: session.participant_token,
                                  answer_text: answer.text,
                                  answer_value: answer.value,
                                  answer_choices: answer.choices,
                                });
                                rememberSubmittedQuestion(q.id);
                              } catch (err: any) {
                                setActionError(err.message || t(locale, "networkRequestFailed"));
                              }
                            }}
                          >
                            {t(locale, "submitAnswer")}
                          </button>
                        )}
                        {answered && <p className="mt-2 text-xs font-medium text-emerald-600">{t(locale, "answerSubmitted")}</p>}
                      </div>
                    );
                  })}
              </div>
            )}

            {actionError && (
              <div className="rounded-[16px] border border-rose-200 bg-rose-50 px-5 py-4 text-[14px] text-rose-700">
                {actionError}
              </div>
            )}

            <div className={platform.feedClass}>
              {session.posts.map((post, postIndex) => {
                const title = post.display_title || post.fetched_title || "Untitled";
                const imageUrl = post.display_image_url || post.fetched_image_url;
                const source = post.source_label || post.fetched_source || hostnameFromUrl(post.original_url);
                const description = post.display_description || post.fetched_description;
                const moreInfoLabel = post.more_info_label || "More Information";
                const isLiked = likedPosts.has(post.id);
                const commentCount =
                  post.display_comments_count + post.comments.length + (participantComments[post.id]?.length || 0);
                const sessionShareBonus = shareSessionRecorded[post.id] ? 1 : 0;
                const displaySharesCount = post.display_shares + sessionShareBonus;

                return (
                  <div key={post.id} data-post-id={post.id} className={platform.cardClass}>
                    <div className={platform.headerClass}>
                      <div className="flex items-center gap-3">
                        <div className={platform.avatarClass}>
                          {source.charAt(0).toUpperCase()}
                        </div>
                        <div>
                          <p className="text-[13px] font-semibold text-[#163047]">{source}</p>
                          <p className="text-[11px] uppercase tracking-[0.2em] text-slate-400">{t(locale, "stimulusPost")}</p>
                        </div>
                      </div>
                    </div>

                    <a
                      href={post.original_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className={`block cursor-pointer text-inherit no-underline ${feedSkin === "douyin" ? "bg-[#111820]" : "bg-white"}`}
                      data-track="headline"
                      onClick={() => {
                        void handleClickPost(post.id);
                      }}
                    >
                      {imageUrl && (
                        <div data-track="image" className={platform.imageWrapClass}>
                          <ExternalPostImage src={imageUrl} alt={title} className={getPostImageClass(feedSkin, platform.imageClass, postIndex)} />
                        </div>
                      )}
                      <div className={platform.bodyClass}>
                        <div className={platform.badgeClass}>
                          {platform.name} · {t(locale, "externalContent")}
                        </div>
                        <h2 className={platform.titleClass}>{title}</h2>
                        {description && (
                          <p className={platform.descriptionClass}>
                            {description}
                          </p>
                        )}
                        <span
                          data-track="more_info"
                          className={platform.moreInfoButtonClass}
                        >
                          <LinkIcon className="h-4 w-4 shrink-0" />
                          <span className="truncate">{moreInfoLabel}</span>
                        </span>
                      </div>
                    </a>

                    <div className={platform.engagementClass}>
                      {post.show_likes && <span>{(post.display_likes + (isLiked ? 1 : 0)).toLocaleString()} {t(locale, "likesLabel")}</span>}
                      {post.show_comments && <span>{commentCount} {t(locale, "comments")}</span>}
                      {post.show_shares && <span>{displaySharesCount} {t(locale, "shares")}</span>}
                    </div>

                    <div className={platform.actionGridClass}>
                      <button
                        data-track="like"
                        type="button"
                        disabled={likeSubmittingPosts.has(post.id)}
                        onClick={() => handleLike(post.id)}
                        className={`${platform.actionButtonClass} ${
                          isLiked ? platform.activeActionClass : ""
                        } disabled:opacity-60`}
                      >
                        {isLiked ? platformActionLabels.liked : platformActionLabels.like}
                      </button>
                      <button
                        data-track="comment"
                        onClick={() => setShowCommentInput(showCommentInput === post.id ? null : post.id)}
                        className={`${platform.actionButtonClass} ${platform.actionButtonDividerClass}`}
                      >
                        {platformActionLabels.comment}
                      </button>
                      <button
                        type="button"
                        data-track="share"
                        disabled={shareSubmittingId === post.id || sessionShareBonus > 0}
                        onClick={() => void handleShareAction(post.id)}
                        className={`${platform.actionButtonClass} ${platform.actionButtonDividerClass} ${
                          sessionShareBonus > 0 ? platform.activeActionClass : ""
                        } disabled:opacity-60`}
                      >
                        {shareSubmittingId === post.id
                          ? t(locale, "shareSaving")
                          : sessionShareBonus > 0
                            ? platformShareRecordedLabel
                            : platformActionLabels.share}
                      </button>
                    </div>

                    {(post.comments.length > 0 || (participantComments[post.id]?.length || 0) > 0) && (
                      <div className="border-t border-slate-200 px-6 py-6">
                        <p className="mb-4 text-[11px] font-semibold uppercase tracking-[0.22em] text-slate-400">{t(locale, "commentThread")}</p>
                        <div className="space-y-3">
                          {post.comments.map((comment) => (
                            <div key={`r-${comment.id}`} className={platform.commentCardClass}>
                              <p className={`text-[13px] font-semibold ${feedSkin === "douyin" ? "text-white" : "text-[#163047]"}`}>{comment.author_name}</p>
                              <p className={`mt-1 text-[13px] leading-6 ${feedSkin === "douyin" ? "text-white/70" : "text-slate-600"}`}>{comment.text}</p>
                            </div>
                          ))}

                          {(participantComments[post.id] || []).map((comment) => (
                            <div key={`p-${comment.id}`} className={platform.participantCommentClass}>
                              <div className="flex items-start justify-between gap-4">
                                <div className="flex-1">
                                  <p className={`text-[12px] font-semibold uppercase tracking-[0.16em] ${platform.accentTextClass}`}>{t(locale, "yourResponse")}</p>
                                  <input
                                    className={`mt-2 w-full border-0 bg-transparent p-0 text-[13px] leading-6 outline-none ${feedSkin === "douyin" ? "text-white/75" : "text-slate-600"}`}
                                    value={comment.text}
                                    onChange={(e) => {
                                      const value = e.target.value;
                                      setParticipantComments((prev) => ({
                                        ...prev,
                                        [post.id]: (prev[post.id] || []).map((item) =>
                                          item.id === comment.id ? { ...item, text: value } : item,
                                        ),
                                      }));
                                    }}
                                    onBlur={async (e) => {
                                      const value = e.target.value;
                                      if (value.trim()) {
                                        try {
                                          setActionError("");
                                          await api.updateParticipantComment(session.response_id, comment.id, value, session.participant_token);
                                        } catch (err: any) {
                                          setActionError(err.message || t(locale, "networkRequestFailed"));
                                        }
                                      }
                                    }}
                                  />
                                </div>
                                <button
                                  className="rounded-full border border-slate-200 px-3 py-1 text-[11px] font-medium text-slate-600 transition hover:bg-slate-50"
                                  onClick={async () => {
                                    try {
                                      setActionError("");
                                      await api.deleteParticipantComment(session.response_id, comment.id, session.participant_token);
                                      setParticipantComments((prev) => ({
                                        ...prev,
                                        [post.id]: (prev[post.id] || []).filter((item) => item.id !== comment.id),
                                      }));
                                    } catch (err: any) {
                                      setActionError(err.message || t(locale, "networkRequestFailed"));
                                    }
                                  }}
                                >
                                  {t(locale, "delete")}
                                </button>
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                    {showCommentInput === post.id && (
                      <div className={`border-t px-6 py-5 ${feedSkin === "douyin" ? "border-white/10 bg-[#111820]" : "border-slate-200 bg-white"}`}>
                        <div className="flex flex-col gap-3 md:flex-row">
                          <input
                            type="text"
                            value={commentInputs[post.id] || ""}
                            onChange={(e) => setCommentInputs((prev) => ({ ...prev, [post.id]: e.target.value }))}
                          placeholder={t(locale, "writeComment")}
                          className={`field-input flex-1 ${feedSkin === "douyin" ? "border-white/15 bg-[#080b10] text-white placeholder:text-white/40" : ""}`}
                          onKeyDown={(e) => e.key === "Enter" && handleComment(post.id)}
                        />
                        <button onClick={() => handleComment(post.id)} className="primary-button min-w-[112px]">
                          {t(locale, "saveResponse")}
                        </button>
                      </div>
                    </div>
                  )}

                  {post.questions && post.questions.length > 0 && (
                    <div className="space-y-4 border-t border-slate-200 bg-white px-5 py-5">
                      <p className={`text-[11px] font-semibold uppercase tracking-[0.22em] ${platform.accentTextClass}`}>{t(locale, "questionBlock")}</p>
                      {post.questions
                          .sort((a, b) => a.order - b.order)
                          .map((q) => {
                            const answered = submittedQuestions.has(q.id);
                            const answer = questionAnswers[q.id] || {};
                            return (
                              <div key={q.id} className={`rounded-[18px] border p-4 ${answered ? "border-emerald-200 bg-emerald-50/60" : "border-slate-200 bg-white"}`}>
                                <p className="text-sm font-semibold text-[#163047]">{q.text}</p>

                                {(q.question_type === "free_text" || q.question_type === "text") && (
                                  <textarea
                                    className="mt-3 w-full rounded-[14px] border border-slate-200 px-3 py-2 text-sm focus:border-[#00a7a0] focus:outline-none focus:ring-4 focus:ring-[#00a7a0]/10"
                                    rows={2}
                                    placeholder={t(locale, "typeYourAnswer")}
                                    disabled={answered}
                                    value={answer.text || ""}
                                    onChange={(e) => setQuestionAnswers((prev) => ({ ...prev, [q.id]: { ...prev[q.id], text: e.target.value } }))}
                                  />
                                )}

                                {(q.question_type === "likert" || q.question_type === "rating") && q.config && (
                                  <div className="mt-3">
                                    <div className="mb-1 flex items-center justify-between text-xs text-slate-500">
                                      <span>{q.config.min_label || "Strongly Disagree"}</span>
                                      <span>{q.config.max_label || "Strongly Agree"}</span>
                                    </div>
                                    <div className="flex gap-2">
                                      {Array.from({ length: (q.config.max ?? 5) - (q.config.min ?? 1) + 1 }, (_, i) => {
                                        const val = (q.config!.min ?? 1) + i;
                                        const selected = answer.value === val;
                                        return (
                                          <button
                                            key={val}
                                            disabled={answered}
                                            onClick={() => setQuestionAnswers((prev) => ({ ...prev, [q.id]: { value: val } }))}
                                            className={`flex-1 rounded-[12px] border py-2 text-sm font-medium transition ${
                                              selected ? "border-[#00a7a0] bg-[#00a7a0] text-white" : "border-slate-200 bg-white text-slate-600 hover:bg-slate-50"
                                            } ${answered ? "opacity-60" : ""}`}
                                          >
                                            {val}
                                          </button>
                                        );
                                      })}
                                    </div>
                                  </div>
                                )}

                                {q.question_type === "multiple_choice" && q.config?.options && (
                                  <div className="mt-3 space-y-2">
                                    {q.config.options.map((opt) => {
                                      const selected = (answer.choices || []).includes(opt);
                                      return (
                                        <button
                                          key={opt}
                                          disabled={answered}
                                          onClick={() => {
                                            setQuestionAnswers((prev) => {
                                              const current = prev[q.id]?.choices || [];
                                              const next = selected ? current.filter((c) => c !== opt) : [...current, opt];
                                              return { ...prev, [q.id]: { choices: next } };
                                            });
                                          }}
                                          className={`block w-full rounded-[12px] border px-3 py-2 text-left text-sm transition ${
                                            selected ? "border-[#00a7a0] bg-[#effcfb] text-[#00847f]" : "border-slate-200 bg-white text-slate-600 hover:bg-slate-50"
                                          } ${answered ? "opacity-60" : ""}`}
                                        >
                                          {opt}
                                        </button>
                                      );
                                    })}
                                  </div>
                                )}

                                {q.question_type === "single_choice" && q.config?.options && (
                                  <div className="mt-3 space-y-2">
                                    {q.config.options.map((opt) => {
                                      const selected = (answer.choices || [])[0] === opt;
                                      return (
                                        <button
                                          key={opt}
                                          disabled={answered}
                                          onClick={() => setQuestionAnswers((prev) => ({ ...prev, [q.id]: { choices: [opt], text: opt } }))}
                                          className={`block w-full rounded-[12px] border px-3 py-2 text-left text-sm transition ${
                                            selected ? "border-[#00a7a0] bg-[#effcfb] text-[#00847f]" : "border-slate-200 bg-white text-slate-600 hover:bg-slate-50"
                                          } ${answered ? "opacity-60" : ""}`}
                                        >
                                          {opt}
                                        </button>
                                      );
                                    })}
                                  </div>
                                )}

                                {!answered && (answer.text || (answer.value !== undefined && answer.value !== null) || (answer.choices && answer.choices.length > 0)) && (
                                  <button
                                    className="primary-button mt-3 px-4 py-2 text-xs"
                                    onClick={async () => {
                                      if (!session) return;
                                      try {
                                        setActionError("");
                                        await api.submitQuestionResponse(session.response_id, q.id, {
                                          question_id: q.id,
                                          participant_token: session.participant_token,
                                          answer_text: answer.text,
                                          answer_value: answer.value,
                                          answer_choices: answer.choices,
                                        });
                                        rememberSubmittedQuestion(q.id);
                                      } catch (err: any) {
                                        setActionError(err.message || t(locale, "networkRequestFailed"));
                                      }
                                    }}
                                  >
                                    {t(locale, "submitAnswer")}
                                  </button>
                                )}
                                {answered && <p className="mt-2 text-xs font-medium text-emerald-600">{t(locale, "answerSubmitted")}</p>}
                              </div>
                            );
                          })}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </main>

          <aside className={platform.rightAsideClass}>
            <div className="surface-panel-soft px-6 py-6">
              <p className={`section-kicker ${platform.accentTextClass}`}>{t(locale, "progress")}</p>
              <p className="mt-3 text-[32px] font-semibold tracking-[-0.06em] text-[#163047]">
                {completedUnits}
              </p>
              <p className="mt-2 text-[13px] leading-6 text-slate-500">{recordedAcrossSummary}</p>
              <div className="mt-4 h-2 overflow-hidden rounded-full bg-slate-200">
                <div className={`h-full rounded-full ${platform.progressClass}`} style={{ width: `${progressValue}%` }} />
              </div>
            </div>

            <div className="surface-panel-soft px-6 py-6">
              <p className={`section-kicker ${platform.accentTextClass}`}>{t(locale, "researchNotes")}</p>
              <div className="mt-5 space-y-4">
                {researchNotes.map((item) => (
                  <div key={item} className="flex gap-3">
                    <CheckCircleIcon className={`mt-0.5 h-4 w-4 ${platform.accentTextClass}`} />
                    <p className="text-[14px] leading-7 text-slate-500">{item}</p>
                  </div>
                ))}
              </div>
            </div>

            <div className="surface-panel px-6 py-6">
              <div className="flex items-start gap-3">
                <UsersIcon className="mt-1 h-4 w-4 text-slate-500" />
                <p className="text-[14px] leading-7 text-slate-500">{t(locale, "stayInSurvey")}</p>
              </div>
              {!canCompleteSurvey && (
                <p className="mt-4 rounded-[14px] bg-amber-50 px-4 py-3 text-[13px] leading-6 text-amber-700">
                  {completionHint}
                </p>
              )}
              <button
                onClick={handleComplete}
                disabled={!canCompleteSurvey || completing}
                className="primary-button mt-6 w-full py-3.5 text-[14px] disabled:cursor-not-allowed disabled:opacity-60"
              >
                {completing ? t(locale, "completionSaving") : t(locale, "complete")}
              </button>
            </div>
          </aside>
        </div>
      </div>
    </div>
  );
}
