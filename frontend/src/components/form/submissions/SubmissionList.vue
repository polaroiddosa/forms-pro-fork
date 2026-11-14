<script setup lang="ts">
// Answers screen (contract C5): table from get_submission_table, one column per question
// plus date and status, Download CSV, click a row to read one answer in full.
import { useManageForm } from "@/stores/form/manageForm";
import { Download } from "@lucide/vue";
import { ListView, Badge, Button, createResource } from "frappe-ui";
import { formatDateTime } from "@/utils/date";
import Drawer from "@/components/ui/Drawer.vue";
import SubmissionDetails from "@/components/form/submissions/SubmissionDetails.vue";
import {
    ANSWER_PREFIX,
    buildListColumns,
    csvFileName,
    flattenRows,
    type TableColumn,
    type TableRow,
} from "@/components/form/submissions/answers";
import { computed, onMounted, ref } from "vue";
import { toast } from "vue-sonner";

const manageFormStore = useManageForm();

const drawerOpen = ref(false);
const selectedRow = ref<TableRow | null>(null);

function onRowClick(row: TableRow) {
    selectedRow.value = row;
    drawerOpen.value = true;
}

const tableResource = createResource({
    url: "forms_pro.api.submission.get_submission_table",
    makeParams() {
        return { form_id: manageFormStore.currentFormId };
    },
    onError(error: Error) {
        toast.error("Failed to fetch answers", { description: error.message });
    },
});

const tableColumns = computed<TableColumn[]>(() => tableResource.data?.columns ?? []);
const rows = computed(() => flattenRows(tableColumns.value, tableResource.data?.rows ?? []));
const listColumns = computed(() => buildListColumns(tableColumns.value));

onMounted(() => {
    tableResource.fetch();
});

// CSV download. The old code set window.location.href to the export URL: a failure (error
// page, permission refusal) replaced the page and nothing was saved. Now the file is
// fetched with the session cookie, checked, and saved through a temporary link.
const downloading = ref(false);
async function downloadCsv() {
    const formId = manageFormStore.currentFormId;
    if (!formId) {
        toast.error("Unable to download", { description: "No form selected." });
        return;
    }
    downloading.value = true;
    try {
        const params = new URLSearchParams({ form_id: formId, file_type: "CSV" });
        const res = await fetch(`/api/method/forms_pro.api.export.export_submissions?${params}`, {
            credentials: "include",
            headers: { "X-Frappe-Site-Name": window.location.hostname },
        });
        const type = res.headers.get("Content-Type") || "";
        if (!res.ok || type.includes("application/json") || type.includes("text/html")) {
            let detail = `The server answered ${res.status}.`;
            try {
                const body = await res.json();
                detail = body._error_message || body.exception || detail;
            } catch {
                /* not JSON */
            }
            toast.error("Download failed", { description: String(detail) });
            return;
        }
        const blob = await res.blob();
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = csvFileName(
            res.headers.get("Content-Disposition"),
            manageFormStore.formData?.title
        );
        document.body.appendChild(a);
        a.click();
        a.remove();
        setTimeout(() => URL.revokeObjectURL(url), 1000);
    } catch (e: any) {
        toast.error("Download failed", { description: e?.message || "Network error." });
    } finally {
        downloading.value = false;
    }
}
</script>
<template>
    <div class="flex">
        <Button :loading="downloading" data-download-csv @click="downloadCsv">
            <template #prefix><Download class="w-4 h-4" /></template>
            Download CSV
        </Button>
    </div>
    <div class="overflow-x-auto" data-answers-table>
        <ListView
            :columns="listColumns"
            :rows="rows"
            :options="{
                selectable: false,
                showTooltip: false,
                onRowClick,
                emptyState: {
                    title: 'No answers yet',
                    description: 'Answers to this form will appear here.',
                },
            }"
            row-key="name"
        >
            <!-- @vue-expect-error -->
            <template #cell="{ item, row, column }">
                <Badge
                    v-if="column.key === 'fp_submission_status'"
                    :label="row.fp_submission_status"
                    :variant="row.fp_submission_status === 'Submitted' ? 'subtle' : 'outline'"
                />
                <span v-else-if="column.key === 'creation'" class="text-sm text-ink-gray-6">
                    {{ formatDateTime(row.creation) }}
                </span>
                <span
                    v-else-if="String(column.key).startsWith(ANSWER_PREFIX)"
                    class="text-sm truncate block"
                    :title="String(item ?? '')"
                >
                    {{ item }}
                </span>
                <span v-else class="text-sm">{{ item }}</span>
            </template>
        </ListView>
    </div>

    <Drawer v-model="drawerOpen" size="lg" title="Answer">
        <SubmissionDetails v-if="selectedRow" :row="selectedRow" :columns="tableColumns" />
    </Drawer>
</template>
