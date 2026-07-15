import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { Card, SeverityBadge, StatusBadge } from "./ui";

describe("ui components", () => {
  it("renders Card title and children", () => {
    render(
      <Card title="Overview">
        <p>Dashboard content</p>
      </Card>,
    );
    expect(screen.getByRole("heading", { name: "Overview" })).toBeInTheDocument();
    expect(screen.getByText("Dashboard content")).toBeInTheDocument();
  });

  it("renders SeverityBadge with severity text", () => {
    render(<SeverityBadge severity="high" />);
    expect(screen.getByText("high")).toBeInTheDocument();
  });

  it("renders StatusBadge with status text", () => {
    render(<StatusBadge status="completed" />);
    expect(screen.getByText("completed")).toBeInTheDocument();
  });
});
