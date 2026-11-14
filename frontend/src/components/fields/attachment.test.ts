import { describe, expect, it } from "vitest";
import {
    AttachmentError,
    MAX_FILE_BYTES,
    attachmentName,
    buildAttachmentValue,
    canAttachAnother,
    checkAttachment,
    countAttachments,
    fileToAttachmentValue,
    markAttached,
} from "./attachment";

describe("checkAttachment", () => {
    it.each(["a.pdf", "a.JPG", "a.jpeg", "a.png", "a.webp", "a.doc", "a.docx"])(
        "accepts %s",
        (name) => {
            expect(checkAttachment({ name, size: 1000 })).toBeNull();
        }
    );
    it.each(["a.exe", "a.svg", "a.html", "a.pdf.js", "noextension", "a.gif"])(
        "refuses type of %s",
        (name) => {
            expect(checkAttachment({ name, size: 1000 })).toMatch(/not accepted/);
        }
    );
    it("refuses a file over 5 MB and accepts exactly 5 MB", () => {
        expect(checkAttachment({ name: "a.pdf", size: MAX_FILE_BYTES + 1 })).toMatch(/5 MB/);
        expect(checkAttachment({ name: "a.pdf", size: MAX_FILE_BYTES })).toBeNull();
    });
    it("refuses an empty file", () => {
        expect(checkAttachment({ name: "a.pdf", size: 0 })).toMatch(/empty/);
    });
});

describe("fileToAttachmentValue", () => {
    it("builds name,data:<mime>;base64,<data>", async () => {
        const file = new File([new Uint8Array([104, 105])], "cv.pdf", { type: "" });
        expect(await fileToAttachmentValue(file)).toBe("cv.pdf,data:application/pdf;base64,aGk=");
    });
    it("takes the mime type from the extension, not from the browser", async () => {
        const file = new File(["x"], "photo.JPG", { type: "text/html" });
        expect(await fileToAttachmentValue(file)).toBe("photo.JPG,data:image/jpeg;base64,eA==");
    });
    it("refuses a wrong type and an oversize file with AttachmentError", async () => {
        await expect(fileToAttachmentValue(new File(["x"], "a.exe"))).rejects.toBeInstanceOf(
            AttachmentError
        );
        const big = new File([new Uint8Array(MAX_FILE_BYTES + 1)], "big.pdf");
        await expect(fileToAttachmentValue(big)).rejects.toThrow(/5 MB/);
    });
    it("handles a 1 MB file without a stack overflow", async () => {
        const file = new File([new Uint8Array(1024 * 1024)], "big.png");
        const value = await fileToAttachmentValue(file);
        expect(value.startsWith("big.png,data:image/png;base64,AAAA")).toBe(true);
    });
});

describe("string helpers", () => {
    it("keeps a comma out of the file name", () => {
        expect(buildAttachmentValue("a,b.pdf", "application/pdf", "QQ==")).toBe(
            "a_b.pdf,data:application/pdf;base64,QQ=="
        );
    });
    it("shows only the name, never the data", () => {
        expect(attachmentName("cv.pdf,data:application/pdf;base64,aGk=")).toBe("cv.pdf");
        expect(attachmentName("")).toBe("");
        expect(attachmentName(undefined)).toBe("");
    });
    it("counts file values", () => {
        expect(countAttachments(["a.pdf,data:application/pdf;base64,QQ==", "", "text", null])).toBe(1);
    });
    it("allows at most 3 files per form", () => {
        markAttached("f1", true);
        markAttached("f2", true);
        markAttached("f3", true);
        expect(canAttachAnother("f4")).toBe(false);
        expect(canAttachAnother("f1")).toBe(true);
        markAttached("f3", false);
        expect(canAttachAnother("f4")).toBe(true);
    });
});
