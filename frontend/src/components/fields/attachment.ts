// Contract C3 (frontend half): a file chosen by a visitor is read in the browser and
// sent as a plain string "<filename>,data:<mime>;base64,<data>" inside the submit
// payload. Frappe's upload_file is never called. The backend re-checks everything.

export const ALLOWED_EXTENSIONS = ["pdf", "jpg", "jpeg", "png", "webp", "doc", "docx"] as const;
export const MAX_FILE_BYTES = 5 * 1024 * 1024;
export const MAX_FILES_PER_FORM = 3;

const MIME_BY_EXTENSION: Record<string, string> = {
    pdf: "application/pdf",
    jpg: "image/jpeg",
    jpeg: "image/jpeg",
    png: "image/png",
    webp: "image/webp",
    doc: "application/msword",
    docx: "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
};

export const ATTACHMENT_HINT = "PDF, JPG, PNG, WEBP, DOC or DOCX, up to 5 MB";

export class AttachmentError extends Error {}

export function fileExtension(name: string): string {
    const dot = name.lastIndexOf(".");
    return dot < 0 ? "" : name.slice(dot + 1).toLowerCase();
}

/** Returns an error message for a file the form refuses, or null when it is fine. */
export function checkAttachment(file: { name: string; size: number }): string | null {
    const ext = fileExtension(file.name);
    if (!(ALLOWED_EXTENSIONS as readonly string[]).includes(ext)) {
        return `This file type is not accepted. Please choose a ${ATTACHMENT_HINT.replace(
            / up to.*$/,
            ""
        )} file.`;
    }
    if (file.size > MAX_FILE_BYTES) {
        return "This file is larger than 5 MB. Please choose a smaller file.";
    }
    if (file.size === 0) {
        return "This file is empty. Please choose another file.";
    }
    return null;
}

/** The file name is separated from the data by a comma, so it may not contain one. */
export function safeFileName(name: string): string {
    return name.replace(/[,\\/\r\n]/g, "_").trim() || "file";
}

export function buildAttachmentValue(name: string, mime: string, base64: string): string {
    return `${safeFileName(name)},data:${mime};base64,${base64}`;
}

function toBase64(bytes: Uint8Array): string {
    let binary = "";
    const chunk = 0x8000;
    for (let i = 0; i < bytes.length; i += chunk) {
        binary += String.fromCharCode(...bytes.subarray(i, i + chunk));
    }
    return btoa(binary);
}

/** Reads a chosen file and returns the value string. Throws AttachmentError when refused. */
export async function fileToAttachmentValue(file: File): Promise<string> {
    const problem = checkAttachment(file);
    if (problem) throw new AttachmentError(problem);
    const bytes = new Uint8Array(await file.arrayBuffer());
    const mime = MIME_BY_EXTENSION[fileExtension(file.name)];
    return buildAttachmentValue(file.name, mime, toBase64(bytes));
}

/** The visible file name of a value string (never the data). */
export function attachmentName(value: unknown): string {
    if (typeof value !== "string" || !value) return "";
    const at = value.indexOf(",data:");
    return at < 0 ? value : value.slice(0, at);
}

/** How many of the given values hold a file. */
export function countAttachments(values: unknown[]): number {
    return values.filter((v) => typeof v === "string" && v.includes(",data:")).length;
}

// Which Attach fields of the form currently hold a file (used for the 3-file limit).
const attachedFields = new Set<string>();
export function markAttached(fieldname: string, attached: boolean) {
    if (attached) attachedFields.add(fieldname);
    else attachedFields.delete(fieldname);
}
export function canAttachAnother(fieldname: string): boolean {
    return attachedFields.has(fieldname) || attachedFields.size < MAX_FILES_PER_FORM;
}
