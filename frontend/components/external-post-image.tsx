"use client";

import { useState } from "react";

type ExternalPostImageProps = {
  src: string;
  className?: string;
  alt?: string;
  loading?: "eager" | "lazy";
};

export function ExternalPostImage({ src, className, alt = "", loading = "lazy" }: ExternalPostImageProps) {
  const [failed, setFailed] = useState(false);
  if (failed) {
    return (
      <div
        className={[
          "flex items-center justify-center bg-slate-100 text-xs font-semibold uppercase tracking-[0.18em] text-slate-400",
          className,
        ]
          .filter(Boolean)
          .join(" ")}
      >
        Image unavailable
      </div>
    );
  }

  return (
    // These images come from arbitrary research stimuli URLs; keeping them browser-loaded avoids proxying them through Next image optimization.
    // eslint-disable-next-line @next/next/no-img-element
    <img
      src={src}
      alt={alt}
      className={className}
      loading={loading}
      decoding="async"
      referrerPolicy="no-referrer"
      onError={() => setFailed(true)}
    />
  );
}
