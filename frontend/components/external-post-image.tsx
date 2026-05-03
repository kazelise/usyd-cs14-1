type ExternalPostImageProps = {
  src: string;
  className?: string;
  alt?: string;
  loading?: "eager" | "lazy";
};

export function ExternalPostImage({ src, className, alt = "", loading = "lazy" }: ExternalPostImageProps) {
  return (
    // These images come from arbitrary research stimuli URLs; keeping them browser-loaded avoids proxying them through Next image optimization.
    // eslint-disable-next-line @next/next/no-img-element
    <img src={src} alt={alt} className={className} loading={loading} decoding="async" referrerPolicy="no-referrer" />
  );
}
