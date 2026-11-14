import { scrubFieldname } from "@/utils/form_layout";

export interface DuplicateQuestion {
  label: string;
  fieldname: string;
}

interface QuestionLike {
  label?: string | null;
  fieldname?: string | null;
}

/**
 * Questions that would end up with the same stored name. The name comes from the
 * Fieldname when one is set, else from the question text (builders never see it).
 */
export function findDuplicateQuestions(fields: QuestionLike[]): DuplicateQuestion[] {
  const seen = new Map<string, QuestionLike>();
  const duplicates: DuplicateQuestion[] = [];

  for (const field of fields) {
    const name = field.fieldname?.trim() ? field.fieldname : scrubFieldname(field.label ?? "");
    if (seen.has(name)) {
      const existing = seen.get(name)!;
      if (!duplicates.some((d) => d.fieldname === name)) {
        duplicates.push({ label: existing.label ?? "", fieldname: name });
      }
      duplicates.push({ label: field.label ?? "", fieldname: name });
    }
    seen.set(name, field);
  }
  return duplicates;
}

function escapeHtml(text: string): string {
  return text
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

/**
 * Wording of the "same question twice" dialog. Builders cannot see the Fieldname,
 * so the text only talks about the question text and never mentions it.
 */
export function duplicateQuestionDialog(duplicates: DuplicateQuestion[]): {
  title: string;
  message: string;
} {
  const labels = Array.from(new Set(duplicates.map((d) => d.label.trim() || "(no text)")));
  const list = labels.map((l) => `<b>${escapeHtml(l)}</b>`).join(", ");
  return {
    title: "Two questions look the same",
    message: `These questions have the same text, or nearly the same: ${list}. Please change the question text of one of them so that each question is different.`,
  };
}
