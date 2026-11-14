// Contract C5 (frontend half): build the answers table from get_submission_table.
export type TableColumn = { fieldname: string; label: string; fieldtype: string };
export type TableRow = {
    name: string;
    creation: string;
    owner?: string;
    fp_submission_status?: string;
    answers: Record<string, string | null | undefined>;
};
export type FlatRow = TableRow & Record<string, any>;

export const ANSWER_PREFIX = "ans__";

/** ListView columns: date, status, then one per question. Keys of answers are prefixed. */
export function buildListColumns(columns: TableColumn[]) {
    return [
        { label: "Date", key: "creation", width: "11rem" },
        { label: "Status", key: "fp_submission_status", width: "7rem" },
        ...columns.map((c) => ({
            label: c.label || c.fieldname,
            key: ANSWER_PREFIX + c.fieldname,
            width: "14rem",
        })),
    ];
}

/** One flat object per row so ListView can read every cell by key. Empty answers become "". */
export function flattenRows(columns: TableColumn[], rows: TableRow[]): FlatRow[] {
    return rows.map((row) => {
        const flat: FlatRow = { ...row };
        for (const c of columns) {
            flat[ANSWER_PREFIX + c.fieldname] = row.answers?.[c.fieldname] ?? "";
        }
        return flat;
    });
}

/** File name for the CSV download, from the response header when present. */
export function csvFileName(contentDisposition: string | null, formTitle?: string): string {
    const match = contentDisposition?.match(/filename\*?=(?:UTF-8'')?"?([^";]+)"?/i);
    if (match) {
        try {
            return decodeURIComponent(match[1]);
        } catch {
            return match[1];
        }
    }
    const base = (formTitle || "answers").replace(/[^\w\- ]+/g, "").trim() || "answers";
    return `${base}.csv`;
}
