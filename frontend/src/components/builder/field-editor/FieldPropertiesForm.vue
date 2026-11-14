<script setup lang="ts">
/**
 * Properties panel for a question. Form builders see only: Question text,
 * Required, Choices (choice questions only), Help text and the folded
 * "Show only if..." section. Fieldname, Fieldtype, Hidden and Default Value are
 * not shown; the fieldname is generated from the question text on save
 * (stores/editForm.ts) or earlier when a "Show only if..." rule refers to it.
 */
import { useEditForm } from "@/stores/editForm";
import { FormControl } from "frappe-ui";
import { FormField } from "@/types/formfield";
import { Fieldtype } from "@/types/FormsPro/form_field.types";
import { getPaletteLabel } from "@/config/fieldTypes";
import { isChoiceFieldtype } from "@/utils/conditionals";
import { isHeading, isPageBreak } from "@/utils/form_layout";
import { computed } from "vue";
import type { Component } from "vue";
import ConditionalLogicSection from "./ConditionalLogicSection.vue";

const editFormStore = useEditForm();

type FieldProperty = {
    fieldname: keyof FormField;
    component: Component;
    props: Record<string, any>;
};

const fieldProperties = computed((): FieldProperty[] => {
    const field = editFormStore.selectedField;
    if (!field) return [];
    const type = field.fieldtype as Fieldtype;

    // Headings and page breaks only have text.
    if (isHeading(type) || isPageBreak(type)) {
        return [
            {
                fieldname: "label",
                component: FormControl,
                props: {
                    type: "text",
                    label: isPageBreak(type) ? "Page title" : "Heading text",
                    required: true,
                    variant: "outline",
                },
            },
        ];
    }

    const props: FieldProperty[] = [
        {
            fieldname: "label",
            component: FormControl,
            props: {
                type: "text",
                label: "Question text",
                required: true,
                variant: "outline",
            },
        },
        {
            fieldname: "reqd",
            component: FormControl,
            props: {
                type: "checkbox",
                label: "Required",
                description: "Visitors must answer this question.",
            },
        },
    ];

    if (isChoiceFieldtype(type)) {
        props.push({
            fieldname: "options",
            component: FormControl,
            props: {
                type: "textarea",
                label: "Choices",
                description: "One choice per line.",
                variant: "outline",
                rows: 5,
            },
        });
    }

    props.push(
        {
            fieldname: "description",
            component: FormControl,
            props: {
                type: "textarea",
                label: "Help text",
                description: "Optional. Shown under the question.",
                required: false,
                variant: "outline",
                rows: 3,
            },
        },
        {
            fieldname: "conditional_logic",
            component: ConditionalLogicSection,
            props: {},
        }
    );
    return props;
});
</script>
<template>
    <div
        class="flex flex-col gap-6 p-4 w-full"
        data-form-builder-component="field-properties-form"
    >
        <div class="flex flex-col gap-1">
            <h3 class="text-lg font-medium">Edit question</h3>
            <span
                v-if="editFormStore.selectedField"
                class="text-xs text-ink-gray-5"
                data-testid="field-type-name"
            >
                {{ getPaletteLabel(editFormStore.selectedField.fieldtype) }}
            </span>
        </div>
        <hr />
        <template v-if="editFormStore.selectedField">
            <template v-for="property in fieldProperties" :key="property.fieldname">
                <component
                    :is="property.component"
                    v-model="editFormStore.selectedField[property.fieldname]"
                    v-bind="property.props"
                />
            </template>
        </template>
    </div>
</template>
