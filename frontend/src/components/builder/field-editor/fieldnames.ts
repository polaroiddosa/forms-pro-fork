import { scrubFieldname } from "@/utils/form_layout";
import type { FormField } from "@/types/formfield";

/**
 * Builders never see or type a Fieldname. It is generated from the question text
 * when the form is saved (stores/editForm.ts). The "Show only if..." rule has to
 * refer to a question by fieldname before that save happens, so this assigns the
 * fieldname early, only for the questions a rule refers to, and keeps it unique.
 * Once set it never changes when the label is edited, so rules do not break.
 */
export function ensureFieldname(field: FormField, allFields: FormField[]): string {
  if (field.fieldname && field.fieldname.trim()) return field.fieldname;

  const taken = new Set(
    allFields
      .filter((f) => f !== field)
      .map((f) => (f.fieldname && f.fieldname.trim()) || scrubFieldname(f.label ?? ""))
      .filter(Boolean)
  );
  const base = scrubFieldname(field.label ?? "") || `question_${(field.idx ?? 0) || allFields.indexOf(field) + 1}`;
  let name = base;
  let n = 2;
  while (taken.has(name)) name = `${base}_${n++}`;
  field.fieldname = name;
  return name;
}
