<script setup lang="ts">
// Contract C3 (frontend half): plain file input, the file is read in the browser and the
// value becomes "<name>,data:<mime>;base64,<data>". Frappe's upload_file is never called.
import { Button, ErrorMessage } from "frappe-ui";
import { ref, computed, onMounted } from "vue";
import {
    ATTACHMENT_HINT,
    AttachmentError,
    ALLOWED_EXTENSIONS,
    attachmentName,
    canAttachAnother,
    fileToAttachmentValue,
    markAttached,
    MAX_FILES_PER_FORM,
} from "./attachment";

const props = defineProps({
    field: {
        type: Object,
        required: true,
    },
});

const value = defineModel<string>();

const input = ref<HTMLInputElement | null>(null);
const error = ref("");
const reading = ref(false);
const fileSize = ref<number | null>(null);

const fileName = computed(() => attachmentName(value.value));
const accept = ALLOWED_EXTENSIONS.map((e) => `.${e}`).join(",");

onMounted(() => markAttached(props.field.fieldname, Boolean(fileName.value)));

const formatFileSize = (size: number) => {
    if (size < 1024) return `${size} B`;
    if (size < 1024 * 1024) return `${(size / 1024).toFixed(1)} KB`;
    return `${(size / 1024 / 1024).toFixed(2)} MB`;
};

const handleChange = async (event: Event) => {
    const target = event.target as HTMLInputElement;
    const file = target.files?.[0];
    target.value = ""; // so choosing the same file again fires change
    if (!file) return;
    error.value = "";
    if (!canAttachAnother(props.field.fieldname)) {
        error.value = `You can attach at most ${MAX_FILES_PER_FORM} files to one form.`;
        return;
    }
    reading.value = true;
    try {
        value.value = await fileToAttachmentValue(file);
        fileSize.value = file.size;
        markAttached(props.field.fieldname, true);
    } catch (e) {
        error.value =
            e instanceof AttachmentError ? e.message : "This file could not be read. Try again.";
    } finally {
        reading.value = false;
    }
};

const handleRemove = () => {
    value.value = "";
    fileSize.value = null;
    error.value = "";
    markAttached(props.field.fieldname, false);
};
</script>
<template>
    <div class="flex gap-2 flex-col mt-2" data-attachment-field>
        <input
            ref="input"
            type="file"
            class="hidden"
            :accept="accept"
            data-attachment-input
            @change="handleChange"
        />
        <template v-if="!fileName">
            <Button
                type="button"
                class="w-full sm:w-auto"
                :loading="reading"
                data-attachment-choose
                @click="input?.click()"
            >
                Choose file
            </Button>
            <span class="text-xs text-ink-gray-5">{{ ATTACHMENT_HINT }}</span>
        </template>
        <div
            v-else
            class="p-3 bg-white border rounded-md flex items-center justify-between gap-3"
            data-attachment-chosen
        >
            <div class="min-w-0">
                <div class="text-sm font-medium truncate" data-attachment-name>{{ fileName }}</div>
                <div v-if="fileSize !== null" class="text-xs text-gray-500">
                    {{ formatFileSize(fileSize) }}
                </div>
            </div>
            <Button
                type="button"
                theme="red"
                variant="subtle"
                label="Remove"
                data-attachment-remove
                @click="handleRemove"
            />
        </div>
        <ErrorMessage :message="error" data-attachment-error />
    </div>
</template>
