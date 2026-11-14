import { describe, expect, it } from "vitest";
import { answersLabel, publicFormLink } from "./publicLink";

describe("publicFormLink", () => {
  it("builds the /f/<route> link", () => {
    expect(publicFormLink("forms_pro_ab12cd34", "https://forms.example.org")).toBe(
      "https://forms.example.org/f/forms_pro_ab12cd34"
    );
  });
  it("keeps slashes inside a route and trims the origin", () => {
    expect(publicFormLink("s/open day", "https://x.org/")).toBe("https://x.org/f/s/open%20day");
  });
  it("is empty without a route", () => {
    expect(publicFormLink("", "https://x.org")).toBe("");
    expect(publicFormLink(null, "https://x.org")).toBe("");
  });
});

describe("answersLabel", () => {
  it("handles zero, one and many", () => {
    expect(answersLabel(0)).toBe("No answers yet");
    expect(answersLabel(undefined)).toBe("No answers yet");
    expect(answersLabel(1)).toBe("1 answer");
    expect(answersLabel(12)).toBe("12 answers");
  });
});
