import * as React from "react";
import { Slot } from "@radix-ui/react-slot";
import { cva, type VariantProps } from "class-variance-authority";

import { cn } from "@/lib/utils";

const buttonVariants = cva(
  "inline-flex items-center justify-center gap-2 whitespace-nowrap text-sm font-semibold transition disabled:pointer-events-none disabled:opacity-40 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#8cc7cf]/60",
  {
    variants: {
      variant: {
        default: "bg-[#ff693b] text-[#07141e] hover:bg-[#ff8b61]",
        secondary: "border border-[#385560] bg-[#102431] text-[#d8d1bf] hover:border-[#8cc7cf] hover:bg-[#17303d]",
        ghost: "text-[#8fa2a7] hover:bg-[#17303d] hover:text-[#fffaf0]",
        destructive: "bg-[#4a292a] text-[#ffc1b8] hover:bg-[#633332]",
      },
      size: {
        default: "h-10 rounded-lg px-4 py-2",
        sm: "h-8 rounded-md px-3 text-xs",
        icon: "size-10 rounded-lg",
      },
    },
    defaultVariants: { variant: "default", size: "default" },
  },
);

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {
  asChild?: boolean;
}

export function Button({ className, variant, size, asChild = false, ...props }: ButtonProps) {
  const Comp = asChild ? Slot : "button";
  return <Comp className={cn(buttonVariants({ variant, size, className }))} {...props} />;
}
