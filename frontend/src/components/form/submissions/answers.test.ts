import { describe, expect, it } from "vitest";
import { ANSWER_PREFIX, buildListColumns, csvFileName, flattenRows } from "./answers";

const columns = [
    { fieldname: "full_name", label: "Full name", fieldtype: "Data" },
    { fieldname: "cv", label: "CV", fieldtype: "Attach" },
];

describe("answers table", () => {
    it("has date, status, then one column per question", () => {
        const cols = buildListColumns(columns);
        expect(cols.map((c) => c.label)).toEqual(["Date", "Status", "Full name", "CV"]);
        expect(cols[2].key).toBe(ANSWER_PREFIX + "full_name");
    });
    it("flattens answers and fills missing ones with empty text", () => {
        const [row] = flattenRows(columns, [
            { name: "r1", creation: "2026-11-14", answers: { full_name: "Asha" } },
        ]);
        expect(row[ANSWER_PREFIX + "full_name"]).toBe("Asha");
        expect(row[ANSWER_PREFIX + "cv"]).toBe("");
    });
    it("takes the CSV name from the header, else from the form title", () => {
        expect(csvFileName('attachment; filename="Enquiry.csv"')).toBe("Enquiry.csv");
        expect(csvFileName(null, "Open day / 2026")).toBe("Open day  2026.csv");
        expect(csvFileName(null)).toBe("answers.csv");
    });
});
