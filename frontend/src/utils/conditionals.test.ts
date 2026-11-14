import { describe, it, expect, vi } from "vitest";

// The real registry imports Vue components and frappe-ui; the rules under test
// only need to know which types are boolean.
vi.mock("@/config/fieldTypes", () => ({
  getFieldTypeDef: (name: string) => ({
    isBoolean: name === "Checkbox" || name === "Switch",
  }),
}));

import {
  shouldFieldBeVisible,
  getVisibleFields,
  getEarlierQuestions,
  getChoices,
  isChoiceFieldtype,
} from "./conditionals";
import { Actions, ConditionalOperators } from "@/types/conditional-render.types";
import { Fieldtype, type FormField } from "@/types/formfield";

function q(
  fieldname: string,
  fieldtype: Fieldtype,
  extra: Partial<FormField> = {}
): FormField {
  return { label: fieldname, fieldname, fieldtype, ...extra } as FormField;
}

function rule(
  target: string,
  source: string,
  value: string,
  action: Actions = Actions.ShowField,
  operator: ConditionalOperators = ConditionalOperators.Is
) {
  return JSON.stringify({
    conditions: [{ fieldname: source, operator, value }],
    action,
    target_field: target,
  });
}

describe("shouldFieldBeVisible: Show Field target (contract C6)", () => {
  const fields = [
    q("course", Fieldtype.SINGLE_CHOICE, { options: "Art\nMusic" }),
    // Target of a Show Field rule; its own Hidden box is NOT ticked.
    q("art_level", Fieldtype.DATA, {
      conditional_logic: rule("art_level", "course", "Art"),
    }),
  ];

  it("is hidden until the conditions are met, without Hidden ticked", () => {
    expect(shouldFieldBeVisible(fields[1], {}, fields)).toBe(false);
    expect(shouldFieldBeVisible(fields[1], { course: "Music" }, fields)).toBe(false);
  });

  it("appears when the conditions are met", () => {
    expect(shouldFieldBeVisible(fields[1], { course: "Art" }, fields)).toBe(true);
  });

  it("disappears again when the answer changes", () => {
    expect(shouldFieldBeVisible(fields[1], { course: "Art" }, fields)).toBe(true);
    expect(shouldFieldBeVisible(fields[1], { course: "Music" }, fields)).toBe(false);
  });

  it("works when the rule is stored on a different question than the target", () => {
    const f = [
      q("course", Fieldtype.SELECT, {
        conditional_logic: rule("art_level", "course", "Art"),
      }),
      q("art_level", Fieldtype.DATA),
    ];
    expect(shouldFieldBeVisible(f[1], {}, f)).toBe(false);
    expect(shouldFieldBeVisible(f[1], { course: "Art" }, f)).toBe(true);
  });

  it("leaves questions without a rule visible", () => {
    expect(shouldFieldBeVisible(fields[0], {}, fields)).toBe(true);
  });

  it("keeps an explicitly hidden question without a rule hidden", () => {
    const f = [q("secret", Fieldtype.DATA, { hidden: true })];
    expect(shouldFieldBeVisible(f[0], {}, f)).toBe(false);
  });

  it("getVisibleFields drops the unmet Show Field target", () => {
    expect(getVisibleFields(fields, {}).map((f) => f.fieldname)).toEqual(["course"]);
    expect(getVisibleFields(fields, { course: "Art" }).map((f) => f.fieldname)).toEqual([
      "course",
      "art_level",
    ]);
  });
});

describe("shouldFieldBeVisible: Hide Field target", () => {
  const fields = [
    q("course", Fieldtype.SELECT, { options: "Art\nMusic" }),
    q("note", Fieldtype.DATA, {
      conditional_logic: rule("note", "course", "Art", Actions.HideField),
    }),
  ];

  it("stays visible until the conditions are met", () => {
    expect(shouldFieldBeVisible(fields[1], {}, fields)).toBe(true);
    expect(shouldFieldBeVisible(fields[1], { course: "Music" }, fields)).toBe(true);
  });

  it("is hidden once the conditions are met", () => {
    expect(shouldFieldBeVisible(fields[1], { course: "Art" }, fields)).toBe(false);
  });
});

describe("conditions on Multiple choice answers (arrays)", () => {
  const fields = [
    q("interests", Fieldtype.MULTISELECT, { options: "Art\nArtisan\nMusic" }),
    q("art_note", Fieldtype.DATA, {
      conditional_logic: rule("art_note", "interests", "Art"),
    }),
  ];

  it("matches a picked choice exactly", () => {
    expect(shouldFieldBeVisible(fields[1], { interests: ["Art", "Music"] }, fields)).toBe(true);
  });

  it("does not match a choice that only contains the text", () => {
    expect(shouldFieldBeVisible(fields[1], { interests: ["Artisan"] }, fields)).toBe(false);
  });

  it("is hidden with nothing picked", () => {
    expect(shouldFieldBeVisible(fields[1], { interests: [] }, fields)).toBe(false);
  });
});

describe("builder helpers", () => {
  it("getChoices splits one choice per line and drops blanks", () => {
    expect(getChoices({ options: "A\n\n B \nC\n" })).toEqual(["A", "B", "C"]);
    expect(getChoices({ options: undefined })).toEqual([]);
  });

  it("isChoiceFieldtype covers Dropdown, Single choice and Multiple choice only", () => {
    expect(isChoiceFieldtype(Fieldtype.SELECT)).toBe(true);
    expect(isChoiceFieldtype(Fieldtype.SINGLE_CHOICE)).toBe(true);
    expect(isChoiceFieldtype(Fieldtype.MULTISELECT)).toBe(true);
    expect(isChoiceFieldtype(Fieldtype.DATA)).toBe(false);
  });

  it("getEarlierQuestions returns only earlier, non-heading questions", () => {
    const a = q("a", Fieldtype.DATA, { row_index: 0 });
    const h = q("h", Fieldtype.HEADING_2, { row_index: 1 });
    const b = q("b", Fieldtype.SELECT, { row_index: 2 });
    const c = q("c", Fieldtype.DATA, { row_index: 3 });
    const all = [c, a, h, b]; // array order differs from reading order
    expect(getEarlierQuestions(c, all).map((f) => f.fieldname).sort()).toEqual(["a", "b"]);
    expect(getEarlierQuestions(a, all)).toEqual([]);
  });
});
