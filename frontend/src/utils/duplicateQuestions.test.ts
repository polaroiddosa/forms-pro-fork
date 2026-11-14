import { describe, expect, it } from "vitest";
import { duplicateQuestionDialog, findDuplicateQuestions } from "./duplicateQuestions";

describe("duplicate question dialog", () => {
  it("finds two questions with the same text", () => {
    const dups = findDuplicateQuestions([{ label: "Your name" }, { label: "Phone" }, { label: "Your name" }]);
    expect(dups.map((d) => d.label)).toEqual(["Your name", "Your name"]);
  });
  it("finds nothing when all questions differ", () => {
    expect(findDuplicateQuestions([{ label: "A" }, { label: "B" }])).toEqual([]);
  });
  it("tells the builder to change the question text and never mentions Fieldname", () => {
    const { title, message } = duplicateQuestionDialog(
      findDuplicateQuestions([{ label: "Your name" }, { label: "Your name" }])
    );
    expect(message).toContain("<b>Your name</b>");
    expect(message).toContain("change the question text");
    expect(`${title} ${message}`).not.toMatch(/field\s*name/i);
    expect(message).not.toContain("your_name");
  });
  it("lists each question text once and escapes html", () => {
    const { message } = duplicateQuestionDialog([
      { label: "<i>x</i>", fieldname: "x" },
      { label: "<i>x</i>", fieldname: "x" },
    ]);
    expect(message.match(/&lt;i&gt;x&lt;\/i&gt;/g)).toHaveLength(1);
    expect(message).not.toContain("<i>");
  });
});
