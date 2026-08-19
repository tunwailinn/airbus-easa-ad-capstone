import * as React from "react";
import { Slot } from "@radix-ui/react-slot";
import { cva, type VariantProps } from "class-variance-authority";

import { cn } from "@/lib/utils";

const buttonVariants = cva(
  "inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-lg text-sm font-medium transition disabled:pointer-events-none disabled:opacity-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#58a6ff]/50",
  {
    variants: {
      variant: {
        default: "bg-[#2f81f7] text-white hover:bg-[#4a91f8]",
        secondary: "border border-[#2b465f] bg-[#102336] text-[#c7d7e5] hover:border-[#4a7397] hover:bg-[#142b41]",
        ghost: "text-[#9eb2c4] hover:bg-[#14273a] hover:text-white",
        destructive: "bg-[#3b252b] text-[#ffaaa5] hover:bg-[#4a2930]",
      },
      size: {
        default: "h-10 px-4 py-2",
        sm: "h-8 rounded-md px-3 text-xs",
        icon: "size-10",
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
