import type { SVGProps } from "react";

export function HealthLinkMark({
  className,
  ...props
}: SVGProps<SVGSVGElement>) {
  return (
    <svg
      aria-hidden="true"
      className={className}
      fill="none"
      viewBox="0 0 48 48"
      {...props}
    >
      <rect fill="currentColor" height="48" rx="15" width="48" />
      <path
        d="M24 12.5v23M12.5 24h23"
        stroke="white"
        strokeLinecap="round"
        strokeWidth="5"
      />
      <path
        d="M15.5 32.5c3.7-1.5 5.5-4.1 6.2-7.7.7-3.7 2.8-6.2 6.3-7.6 1.7-.7 3.2-.9 4.5-.7"
        opacity=".32"
        stroke="white"
        strokeLinecap="round"
        strokeWidth="2.4"
      />
    </svg>
  );
}
