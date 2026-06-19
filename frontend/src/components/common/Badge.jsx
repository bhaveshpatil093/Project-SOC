import { clsx } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs) {
  return twMerge(clsx(inputs));
}

import React from "react";

export const Badge = React.memo(({ children, className, variant = "default" }) => {
  const v = (variant || "default").toLowerCase();
  
  const variants = {
    default: "bg-[var(--bg_tertiary)] text-[var(--text_primary)]",
    critical: "bg-red-500/10 text-red-500 border border-red-500/50",
    high: "bg-orange-500/10 text-orange-500 border border-orange-500/50",
    medium: "bg-yellow-500/10 text-yellow-500 border border-yellow-500/50",
    low: "bg-green-500/10 text-green-500 border border-green-500/50",
    open: "bg-blue-500/10 text-blue-500 border border-blue-500/50",
    closed: "bg-[var(--text_secondary)]/10 text-[var(--text_secondary)] border border-[var(--border)]",
    in_progress: "bg-purple-500/10 text-purple-400 border border-purple-500/50",
    tp: "bg-red-500/10 text-red-500 border border-red-500/50",
    fp: "bg-[var(--text_secondary)]/10 text-[var(--text_secondary)] border border-[var(--border)]",
    benign: "bg-green-500/10 text-green-500 border border-green-500/50",
  };

  return (
    <span className={cn("px-2.5 py-0.5 rounded-full text-xs font-semibold uppercase tracking-wider", variants[v] || variants.default, className)}>
      {children}
    </span>
  );
});
