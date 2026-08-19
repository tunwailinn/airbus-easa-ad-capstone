import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { Button } from "@/components/ui/button";

describe("Button", () => {
  it("renders an accessible button and respects disabled state", () => {
    render(<Button disabled>Ask assistant</Button>);
    expect(screen.getByRole("button", { name: "Ask assistant" })).toBeDisabled();
  });
});
