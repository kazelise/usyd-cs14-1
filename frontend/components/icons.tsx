type IconProps = {
  className?: string;
};

function IconFrame({ className, children }: IconProps & { children: React.ReactNode }) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className || "h-5 w-5"}
      aria-hidden="true"
    >
      {children}
    </svg>
  );
}

export function SurveyIcon({ className }: IconProps) {
  return (
    <IconFrame className={className}>
      <rect x="4" y="5" width="16" height="14" rx="2" />
      <path d="M8 9h8" />
      <path d="M8 13h8" />
      <path d="M8 17h5" />
    </IconFrame>
  );
}

export function TemplateIcon({ className }: IconProps) {
  return (
    <IconFrame className={className}>
      <rect x="4" y="5" width="7" height="6" rx="1.5" />
      <rect x="13" y="5" width="7" height="6" rx="1.5" />
      <rect x="4" y="13" width="7" height="6" rx="1.5" />
      <rect x="13" y="13" width="7" height="6" rx="1.5" />
    </IconFrame>
  );
}

export function ChartIcon({ className }: IconProps) {
  return (
    <IconFrame className={className}>
      <path d="M5 19h14" />
      <path d="M7 15v-4" />
      <path d="M12 15V8" />
      <path d="M17 15v-7" />
    </IconFrame>
  );
}

export function BellIcon({ className }: IconProps) {
  return (
    <IconFrame className={className}>
      <path d="M8 18h8" />
      <path d="M10 21h4" />
      <path d="M6 18V11a6 6 0 1 1 12 0v7" />
    </IconFrame>
  );
}

export function HelpIcon({ className }: IconProps) {
  return (
    <IconFrame className={className}>
      <circle cx="12" cy="12" r="9" />
      <path d="M9.5 9a2.5 2.5 0 1 1 4.1 2c-.9.7-1.6 1.1-1.6 2.3" />
      <path d="M12 17h.01" />
    </IconFrame>
  );
}

export function WorkspaceIcon({ className }: IconProps) {
  return (
    <IconFrame className={className}>
      <path d="m12 3 7 4-7 4-7-4 7-4Z" />
      <path d="m5 7 7 4 7-4" />
      <path d="M5 7v8l7 4 7-4V7" />
    </IconFrame>
  );
}

export function SearchIcon({ className }: IconProps) {
  return (
    <IconFrame className={className}>
      <circle cx="11" cy="11" r="6" />
      <path d="m20 20-4.2-4.2" />
    </IconFrame>
  );
}

export function PlusIcon({ className }: IconProps) {
  return (
    <IconFrame className={className}>
      <path d="M12 5v14" />
      <path d="M5 12h14" />
    </IconFrame>
  );
}

export function UsersIcon({ className }: IconProps) {
  return (
    <IconFrame className={className}>
      <path d="M16.5 19a4.5 4.5 0 0 0-9 0" />
      <circle cx="12" cy="9" r="3" />
      <path d="M18.5 19a3.5 3.5 0 0 0-2.7-3.4" />
      <path d="M8.2 15.6A3.5 3.5 0 0 0 5.5 19" />
    </IconFrame>
  );
}

export function DraftIcon({ className }: IconProps) {
  return (
    <IconFrame className={className}>
      <path d="M4 20h4l10-10-4-4L4 16v4Z" />
      <path d="m13 7 4 4" />
    </IconFrame>
  );
}

export function ArchiveIcon({ className }: IconProps) {
  return (
    <IconFrame className={className}>
      <rect x="4" y="5" width="16" height="4" rx="1" />
      <path d="M6 9h12v9a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2V9Z" />
      <path d="M10 13h4" />
    </IconFrame>
  );
}

export function SettingsIcon({ className }: IconProps) {
  return (
    <IconFrame className={className}>
      <circle cx="12" cy="12" r="3" />
      <path d="m19 12 1.5-1-1.2-2.2-1.8.2a6.9 6.9 0 0 0-1.3-1.3l.2-1.8L14.2 4.5 13 6a6.9 6.9 0 0 0-2 0L9.8 4.5 7.6 5.7l.2 1.8A6.9 6.9 0 0 0 6.5 8.8l-1.8-.2L3.5 11 5 12a6.9 6.9 0 0 0 0 2l-1.5 1 1.2 2.2 1.8-.2a6.9 6.9 0 0 0 1.3 1.3l-.2 1.8 2.2 1.2L11 18a6.9 6.9 0 0 0 2 0l1.2 1.5 2.2-1.2-.2-1.8a6.9 6.9 0 0 0 1.3-1.3l1.8.2 1.2-2.2L19 12Z" />
    </IconFrame>
  );
}

export function SupportIcon({ className }: IconProps) {
  return (
    <IconFrame className={className}>
      <path d="M4 12a8 8 0 0 1 16 0" />
      <path d="M5 15a2 2 0 0 0 2 2h1v-5H7a2 2 0 0 0-2 2v1Z" />
      <path d="M19 15a2 2 0 0 1-2 2h-1v-5h1a2 2 0 0 1 2 2v1Z" />
      <path d="M12 20h2" />
    </IconFrame>
  );
}

export function LinkIcon({ className }: IconProps) {
  return (
    <IconFrame className={className}>
      <path d="M10 14 8 16a3 3 0 1 1-4-4l3-3a3 3 0 0 1 4 0" />
      <path d="m14 10 2-2a3 3 0 1 1 4 4l-3 3a3 3 0 0 1-4 0" />
      <path d="m9 15 6-6" />
    </IconFrame>
  );
}

export function GlobeIcon({ className }: IconProps) {
  return (
    <IconFrame className={className}>
      <circle cx="12" cy="12" r="9" />
      <path d="M3 12h18" />
      <path d="M12 3a15 15 0 0 1 0 18" />
      <path d="M12 3a15 15 0 0 0 0 18" />
    </IconFrame>
  );
}

export function CheckCircleIcon({ className }: IconProps) {
  return (
    <IconFrame className={className}>
      <circle cx="12" cy="12" r="9" />
      <path d="m8.5 12 2.2 2.2 4.8-4.8" />
    </IconFrame>
  );
}

export function ChevronLeftIcon({ className }: IconProps) {
  return (
    <IconFrame className={className}>
      <path d="m15 18-6-6 6-6" />
    </IconFrame>
  );
}

export function ChevronRightIcon({ className }: IconProps) {
  return (
    <IconFrame className={className}>
      <path d="m9 18 6-6-6-6" />
    </IconFrame>
  );
}