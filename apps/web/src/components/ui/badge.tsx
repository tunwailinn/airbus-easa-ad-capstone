import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";

import { cn } from "@/lib/utils";

const badgeVariants = cva("inline-flex items-center rounded-md border px-2.5 py-1 text-[10px] font-semibold uppercase tracking-[0.08em]", {
  variants: {
    variant: {
      default: "border-[#49636c] bg-[#17303d] text-[#b7d2d4]",
      success: "border-[#5d9f86]/50 bg-[#80cfb0]/10 text-[#9de2c8]",
      warning: "border-[#b38a3e]/50 bg-[#e5b75c]/10 text-[#f0cd88]",
      danger: "border-[#b85b52]/50 bg-[#ef7b6d]/10 text-[#ffaaa0]",
    },
  },
  defaultVariants: { variant: "default" },
});

export interface BadgeProps extends React.HTMLAttributes<HTMLSpanElement>, VariantProps<typeof badgeVariants> {}

export function Badge({ className, variant, ...props }: BadgeProps) {
  return <span className={cn(badgeVariants({ variant }), className)} {...props} />;
}
