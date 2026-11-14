<script setup lang="ts">
import { Badge, Button } from "frappe-ui";
import { FileText, Link as LinkIcon, Check } from "@lucide/vue";
import { computed, ref } from "vue";
import { toast } from "vue-sonner";
import { answersLabel, copyText, publicFormLink } from "@/utils/publicLink";

const props = defineProps({
    form: {
        type: Object,
        required: true,
    },
});

const formattedDate = computed(() => {
    return new Date(props.form.creation).toLocaleDateString();
});

const answersText = computed(() => answersLabel(props.form.submission_count));
const link = computed(() => publicFormLink(props.form.route, window.location.origin));

const copied = ref(false);
async function copyLink() {
    if (!link.value) return;
    if (await copyText(link.value)) {
        copied.value = true;
        toast.success("Link copied");
        setTimeout(() => (copied.value = false), 2000);
    } else {
        toast.error("Could not copy the link");
    }
}
</script>
<template>
    <div
        @click="$router.push({ name: 'Manage Form', params: { id: props.form.name } })"
        class="flex flex-col gap-2 border rounded p-4 hover:border-gray-400 transition-all duration-300 cursor-pointer"
    >
        <div class="flex flex-col gap-3 text-ink-gray-6">
            <FileText class="w-5 h-5" />
            <h3 class="text-lg font-medium">{{ props.form.title }}</h3>
            <div class="flex gap-2 items-center">
                <Badge
                    class="w-fit"
                    :label="props.form.is_published ? 'Published' : 'Draft'"
                    :theme="props.form.is_published ? 'green' : 'gray'"
                />
                <p class="text-sm text-ink-gray-4">{{ formattedDate }}</p>
            </div>
            <p class="text-sm text-ink-gray-6" data-form-card-answers>{{ answersText }}</p>
        </div>
        <Button
            v-if="link"
            class="w-fit"
            variant="subtle"
            data-form-card-copy-link
            :label="copied ? 'Copied' : 'Copy link'"
            @click.stop="copyLink"
        >
            <template #prefix>
                <Check v-if="copied" class="w-4 h-4" />
                <LinkIcon v-else class="w-4 h-4" />
            </template>
        </Button>
    </div>
</template>
