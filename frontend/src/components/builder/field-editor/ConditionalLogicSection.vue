<script setup lang="ts">
/**
 * "Show only if..." (folded away by default).
 *
 * The rule belongs to the question being edited: it is stored as that field's own
 * `conditional_logic` with `target_field` = its own fieldname and action
 * "Show Field". utils/conditionals.ts hides a Show Field target until the
 * conditions are met, so no Hidden tick is needed. One rule per question, one
 * condition: an earlier question, an operator and a value. For Dropdown, Single
 * choice and Multiple choice questions the value is picked from that question's
 * choices; for other questions it is typed.
 */
import { computed, ref, watch } from "vue";
import { ChevronDown, ChevronRight } from "@lucide/vue";
import { Button, FormControl } from "frappe-ui";
import { useEditForm } from "@/stores/editForm";
import {
    ConditionalOperators,
    Actions,
    type ConditionalLogic,
} from "@/types/conditional-render.types";
import type { FormField } from "@/types/formfield";
import {
    getChoices,
    getEarlierQuestions,
    isChoiceFieldtype,
    parseConditionalLogic,
} from "@/utils/conditionals";
import { ensureFieldname } from "./fieldnames";

const editFormStore = useEditForm();

const selected = computed(() => editFormStore.selectedField as FormField | null);
const allFields = computed<FormField[]>(() => editFormStore.fields as FormField[]);

const rule = computed<ConditionalLogic | null>(() =>
    parseConditionalLogic(selected.value?.conditional_logic)
);

// A rule written by the old panel on another question that targets a different one.
const isForeignRule = computed(
    () =>
        !!rule.value &&
        !!selected.value?.fieldname &&
        rule.value.target_field !== selected.value.fieldname
);

const condition = computed(() => rule.value?.conditions?.[0] ?? null);
const open = ref(false);
watch(
    () => selected.value,
    () => {
        open.value = !!rule.value;
    },
    { immediate: true }
);

const earlier = computed(() =>
    selected.value ? getEarlierQuestions(selected.value, allFields.value) : []
);

const questionOptions = computed(() =>
    earlier.value.map((f) => ({
        label: f.label?.trim() || "Untitled question",
        value: String(allFields.value.indexOf(f)),
    }))
);

const pickedQuestion = computed<FormField | undefined>(() =>
    condition.value
        ? earlier.value.find((f) => f.fieldname === condition.value!.fieldname)
        : undefined
);
const pickedIndex = computed(() =>
    pickedQuestion.value ? String(allFields.value.indexOf(pickedQuestion.value)) : ""
);

const pickedIsChoice = computed(() => isChoiceFieldtype(pickedQuestion.value?.fieldtype));
const choiceOptions = computed(() =>
    pickedQuestion.value
        ? getChoices(pickedQuestion.value).map((c) => ({ label: c, value: c }))
        : []
);

const operatorOptions = computed(() => {
    const ops = pickedIsChoice.value
        ? [ConditionalOperators.Is, ConditionalOperators.IsNot]
        : Object.values(ConditionalOperators);
    return ops.map((o) => ({ label: o, value: o }));
});

const showValue = computed(
    () =>
        !!condition.value &&
        ![
            ConditionalOperators.IsEmpty,
            ConditionalOperators.IsNotEmpty,
            ConditionalOperators.IsSet,
        ].includes(condition.value.operator)
);

function write(next: ConditionalLogic | null) {
    if (!selected.value) return;
    selected.value.conditional_logic = next ? JSON.stringify(next) : "";
}

function build(partial: {
    fieldname?: string;
    operator?: ConditionalOperators;
    value?: string;
}): ConditionalLogic {
    const cur = condition.value;
    return {
        conditions: [
            {
                fieldname: partial.fieldname ?? cur?.fieldname ?? "",
                operator: partial.operator ?? cur?.operator ?? ConditionalOperators.Is,
                value: partial.value ?? (cur?.value as string) ?? "",
            },
        ],
        action: Actions.ShowField,
        target_field: ensureFieldname(selected.value!, allFields.value),
    };
}

function pickQuestion(index: string) {
    const f = allFields.value[Number(index)];
    if (!f) return;
    const fieldname = ensureFieldname(f, allFields.value);
    write(build({ fieldname, operator: ConditionalOperators.Is, value: "" }));
}

function pickOperator(operator: ConditionalOperators) {
    write(build({ operator }));
}

function pickValue(value: string) {
    write(build({ value }));
}

function clearRule() {
    write(null);
    open.value = false;
}
</script>

<template>
    <div class="flex flex-col gap-2" data-form-builder-component="show-only-if">
        <button
            type="button"
            class="flex items-center gap-1 text-sm font-medium text-ink-gray-7 w-fit"
            :aria-expanded="open"
            @click="open = !open"
        >
            <component :is="open ? ChevronDown : ChevronRight" class="w-4 h-4" />
            Show only if...
            <span v-if="rule && !open" class="text-xs text-ink-gray-5 font-normal">(set)</span>
        </button>

        <div
            v-if="open"
            class="p-3 bg-surface-gray-1 border rounded flex flex-col gap-3"
        >
            <p v-if="isForeignRule" class="text-sm text-ink-gray-6">
                This question has an older rule that shows or hides a different question.
                It is kept as it is.
            </p>
            <template v-else>
                <p v-if="!earlier.length" class="text-sm text-ink-gray-5">
                    Add a question above this one first. A question can only depend on an
                    earlier question.
                </p>
                <template v-else>
                    <FormControl
                        type="select"
                        label="Earlier question"
                        placeholder="Pick a question"
                        variant="outline"
                        :options="questionOptions"
                        :modelValue="pickedIndex"
                        @update:modelValue="pickQuestion"
                    />
                    <template v-if="condition && pickedQuestion">
                        <FormControl
                            type="select"
                            label="Condition"
                            variant="outline"
                            :options="operatorOptions"
                            :modelValue="condition.operator"
                            @update:modelValue="pickOperator"
                        />
                        <template v-if="showValue">
                            <FormControl
                                v-if="pickedIsChoice"
                                type="select"
                                label="Answer"
                                placeholder="Pick an answer"
                                variant="outline"
                                :options="choiceOptions"
                                :modelValue="String(condition.value ?? '')"
                                @update:modelValue="pickValue"
                            />
                            <FormControl
                                v-else
                                type="text"
                                label="Answer"
                                placeholder="Type the answer"
                                variant="outline"
                                :modelValue="String(condition.value ?? '')"
                                @update:modelValue="pickValue"
                            />
                            <p
                                v-if="pickedIsChoice && !choiceOptions.length"
                                class="text-xs text-ink-gray-5"
                            >
                                That question has no choices yet.
                            </p>
                        </template>
                        <p class="text-xs text-ink-gray-5">
                            This question stays hidden until the answer matches.
                        </p>
                    </template>
                </template>
                <Button
                    v-if="rule"
                    class="w-fit"
                    variant="ghost"
                    theme="red"
                    size="sm"
                    label="Remove this rule"
                    @click="clearRule"
                />
            </template>
        </div>
    </div>
</template>
