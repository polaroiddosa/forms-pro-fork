<script setup lang="ts">
import { ref, computed } from "vue";
import { formFields, type FormFields } from "@/utils/form_fields";
import { PALETTE_ORDER } from "@/config/fieldTypes";
import { Fieldtype } from "@/types/FormsPro/form_field.types";
import { FormControl } from "frappe-ui";
import { useEditForm } from "@/stores/editForm";

const search = ref("");

// Types kept in the registry (existing forms still render them) but not offered
// to form builders. Page Break is added through "Add page" instead.
const HIDDEN_FROM_SIDEBAR = new Set<string>([
    Fieldtype.PAGE_BREAK,
    Fieldtype.PASSWORD,
    Fieldtype.LINK,
    Fieldtype.TABLE,
    Fieldtype.DATE_TIME,
    Fieldtype.DATE_RANGE,
    Fieldtype.TIME_PICKER,
    Fieldtype.TEXT_EDITOR,
    Fieldtype.SWITCH,
    Fieldtype.CHECKBOX,
    Fieldtype.RATING,
    Fieldtype.HEADING_1,
    Fieldtype.HEADING_3,
]);

// Shown in the order of PALETTE_ORDER, with plain-language names.
const filteredFields = computed(() => {
    const q = search.value.toLowerCase();
    return PALETTE_ORDER.map((entry) => ({
        entry,
        def: formFields.find((f: FormFields) => f.name === entry.type),
    }))
        .filter(({ def }) => !!def && !HIDDEN_FROM_SIDEBAR.has(def.name))
        .filter(({ entry }) => entry.label.toLowerCase().includes(q))
        .map(({ entry, def }) => ({
            name: def!.name,
            icon: def!.icon,
            label: entry.label,
        }));
});

const editFormStore = useEditForm();
</script>
<template>
    <div class="space-y-4">
        <h3 class="text-lg font-medium">Add a question</h3>
        <div class="flex flex-col gap-3">
            <FormControl
                v-model="search"
                type="search"
                variant="outline"
                placeholder="Search question types"
            />
            <p v-if="!filteredFields.length" class="text-sm text-gray-500 px-1 py-2">
                No question types match "{{ search }}"
            </p>
            <div v-else class="flex flex-col gap-2">
                <button
                    v-for="field in filteredFields"
                    :key="field.name"
                    type="button"
                    class="flex w-full items-center gap-2 px-2.5 py-2 bg-surface-gray-1 rounded border border-outline-gray-1 hover:border-outline-gray-2 hover:bg-surface-gray-2 active:scale-[0.98] active:bg-surface-gray-3 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-gray-900 focus-visible:ring-offset-1 transition-all duration-150 text-left"
                    @click="editFormStore.addField(field.name)"
                >
                    <component
                        :is="field.icon"
                        class="w-4 h-4 text-gray-600 shrink-0"
                        aria-hidden="true"
                    />
                    <span class="text-sm truncate">{{ field.label }}</span>
                </button>
            </div>
        </div>
    </div>
</template>
