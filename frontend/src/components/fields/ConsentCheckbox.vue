<script setup lang="ts">
// Fixed consent tick shown at the bottom of every public form (contract C1).
// Wording comes from the API keys consent_label and consent_text; builders cannot edit it.
defineProps<{ label: string; text?: string; invalid?: boolean }>();
const ticked = defineModel<boolean>({ default: false });
</script>
<template>
    <div
        class="rounded-md border p-3"
        :class="invalid ? 'border-[#B3261E]' : 'border-outline-gray-2'"
        data-consent
    >
        <label class="flex items-start gap-3 cursor-pointer">
            <input
                v-model="ticked"
                type="checkbox"
                class="mt-1 h-5 w-5 shrink-0 cursor-pointer accent-[#1255AA]"
                data-consent-checkbox
            />
            <span class="text-base font-semibold leading-snug">{{ label }}</span>
        </label>
        <p v-if="text" class="mt-2 ml-8 text-sm leading-snug text-ink-gray-6" data-consent-text>
            {{ text }}
        </p>
    </div>
</template>
