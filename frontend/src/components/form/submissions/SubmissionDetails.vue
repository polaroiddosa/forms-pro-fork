<script setup lang="ts">
// One answer in full. Built from the row of get_submission_table (staff only: that API
// needs read permission on the form). Files are shown as names, never as links.
import { computed } from "vue";
import { formatDateTime } from "@/utils/date";
import type { TableColumn, TableRow } from "./answers";

const props = defineProps<{ row: TableRow; columns: TableColumn[] }>();

const meta = computed(() => [
    { label: "Received", value: formatDateTime(props.row.creation) },
    { label: "Status", value: props.row.fp_submission_status || "" },
    { label: "Reference", value: props.row.name, mono: true },
]);
</script>
<template>
    <div class="flex flex-col gap-4 p-2" data-answer-detail>
        <dl class="grid grid-cols-3 gap-x-4 gap-y-2">
            <template v-for="item in meta" :key="item.label">
                <dt class="text-sm text-ink-gray-5">{{ item.label }}</dt>
                <dd class="text-sm text-ink-gray-8 col-span-2" :class="{ 'font-mono': item.mono }">
                    {{ item.value }}
                </dd>
            </template>
        </dl>
        <hr />
        <dl class="flex flex-col gap-5 my-2">
            <div v-for="c in columns" :key="c.fieldname" class="flex flex-col gap-1">
                <dt class="text-sm text-ink-gray-5">{{ c.label }}</dt>
                <dd class="text-sm text-ink-gray-8 whitespace-pre-wrap break-words">
                    <span v-if="row.answers?.[c.fieldname]">{{ row.answers[c.fieldname] }}</span>
                    <span v-else class="text-ink-gray-4">No answer</span>
                    <span
                        v-if="c.fieldtype === 'Attach' && row.answers?.[c.fieldname]"
                        class="ml-2 text-xs text-ink-gray-5"
                        >(file, open it from the CRM lead)</span
                    >
                </dd>
            </div>
        </dl>
    </div>
</template>
