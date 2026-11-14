<script setup lang="ts">
/**
 * Single choice question: radio buttons, pick one. Used by the builder canvas
 * and the public form (it is the registry component for "Single Choice").
 *
 * Choices are read from `field.options` (one per line) so it does not depend on
 * the shared options loader. The answer is the chosen option's text, which is
 * what the Frappe Select column stores.
 */
import { computed, useId } from "vue";
import { Button } from "frappe-ui";

const props = defineProps<{
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    field?: Record<string, any>;
    disabled?: boolean;
    inEditMode?: boolean;
}>();

const modelValue = defineModel<string | null>({ default: null });
const groupName = `single-choice-${useId()}`;

const choices = computed<string[]>(() =>
    (props.field?.options ?? "")
        .split("\n")
        .map((o: string) => o.trim())
        .filter(Boolean)
);

function removeOption(option: string) {
    if (!props.field) return;
    props.field.options = choices.value.filter((v) => v !== option).join("\n");
    if (modelValue.value === option) modelValue.value = null;
}
</script>

<template>
    <div class="flex flex-col gap-1" role="radiogroup" data-field-type="single-choice">
        <div
            v-for="option in choices"
            :key="option"
            class="flex items-center gap-2 min-h-[32px] rounded px-1 transition"
            :class="[
                inEditMode
                    ? 'hover:bg-surface-gray-2'
                    : 'cursor-pointer hover:bg-surface-gray-2 active:bg-surface-gray-3',
                { 'opacity-50 cursor-not-allowed': disabled },
            ]"
        >
            <label class="flex items-center gap-2 flex-1 cursor-pointer">
                <input
                    type="radio"
                    class="size-4 accent-[#1255AA]"
                    :name="groupName"
                    :value="option"
                    :checked="modelValue === option"
                    :disabled="disabled"
                    @change="modelValue = option"
                />
                <span class="text-base text-ink-gray-8 select-none">{{ option }}</span>
            </label>
            <Button
                v-if="inEditMode"
                variant="ghost"
                icon="x"
                size="sm"
                class="!size-5 pointer-events-auto"
                aria-label="Remove choice"
                @click.stop="removeOption(option)"
            />
        </div>
        <span v-if="!choices.length" class="text-sm text-ink-gray-4 italic">
            No choices yet
        </span>
    </div>
</template>
