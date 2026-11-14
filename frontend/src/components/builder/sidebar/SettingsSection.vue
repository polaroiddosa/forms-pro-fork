<script setup lang="ts">
import { Checkbox, Dialog, FormControl, TextEditor, Tooltip } from "frappe-ui";
import { useEditForm } from "@/stores/editForm";
import { validateFormRoute } from "@/utils/form_generator";
import { ref, watch } from "vue";
import { CircleCheck } from "@lucide/vue";

const editFormStore = useEditForm();

const showValidateMsg = ref(false);
const routeExists = ref(false);

const validateRoute = async () => {
    routeExists.value = await validateFormRoute(
        editFormStore.formData.name,
        editFormStore.formData.route
    );
    showValidateMsg.value = true;
};

watch(
    () => editFormStore.formData.allow_incomplete,
    (newVal) => {
        if (newVal) {
            editFormStore.formData.login_required = true;
        }
        if (!newVal) {
            editFormStore.formData.login_required = editFormStore.originalFormData.login_required;
        }
    }
);

const inExpandedDescription = ref(false);
</script>
<template>
    <div class="space-y-4">
        <h3 class="text-lg font-medium">Settings</h3>
        <div class="flex flex-col gap-3">
            <!-- Fork: Linked DocType and Form ID are not shown to form builders (see SCREEN-LIST-DRAFT.md). -->
            <h5 class="text-sm font-medium mt-4 mb-1">Form link</h5>
            <div class="space-y-6">
                <FormControl
                    required
                    label="Link name"
                    variant="outline"
                    type="text"
                    v-model="editFormStore.formData.route"
                    description="The visitor link ends with /f/ and this name. It must be unique."
                    @change="validateRoute()"
                />
                <div v-if="showValidateMsg" class="text-xs font-medium">
                    <span v-if="routeExists" class="text-red-500 flex items-center gap-1">
                        Route already exists
                    </span>
                    <span v-else class="text-green-500 flex items-center gap-1">
                        <CircleCheck class="w-4 h-4" /> Route is available</span
                    >
                </div>
                <!-- Fork: Login Required and Allow Incomplete Forms are not shown to form builders.
                     Public enquiry forms never need a login, and guests cannot save drafts (F2 refuses them). -->
            </div>

            <h5 class="text-sm font-medium mt-4 mb-1">Success Page</h5>
            <div class="space-y-6">
                <FormControl
                    label="Success Title"
                    variant="outline"
                    type="text"
                    v-model="editFormStore.formData.success_title"
                />
                <div class="flex flex-col gap-2">
                    <span class="text-xs text-ink-gray-5">Success Description</span>
                    <TextEditor
                        variant="outline"
                        :content="editFormStore.formData.success_description"
                        @change="
                            (value: string) => (editFormStore.formData.success_description = value)
                        "
                        editor-class="bg-surface-white w-full rounded-b form-description border rounded-b min-h-24 max-h-24 overflow-y-auto"
                        placeholder="Write a description for the success page"
                        :bubble-menu="true"
                        :starterkit-options="{
                            heading: {
                                levels: [2, 3, 4, 5, 6],
                            },
                        }"
                    />
                    <Dialog
                        v-model="inExpandedDescription"
                        :options="{
                            title: ' ',
                            size: '3xl',
                            icon: 'type',
                            position: 'top',
                        }"
                    >
                        <template #body-content>
                            <div class="space-y-2">
                                <p class="text-base font-medium">Edit Success Description</p>
                                <p class="text-sm text-ink-gray-7">
                                    Changes made here are automatically copied to the success
                                    description field in the sidebar, So you can safely make
                                    changes here and close the dialog.
                                    <br /><br />
                                    But to make the changes live,you need to save the form after
                                    closing the dialog.
                                </p>
                            </div>
                            <div class="mt-6"></div>
                            <TextEditor
                                variant="outline"
                                :content="editFormStore.formData.success_description"
                                @change="
                                    (value: string) =>
                                        (editFormStore.formData.success_description = value)
                                "
                                editor-class="bg-surface-white w-full rounded-b form-description border rounded-b min-h-40 max-w-full"
                                placeholder="Write a description for the success page"
                                :fixed-menu="true"
                                :starterkit-options="{
                                    heading: {
                                        levels: [2, 3, 4, 5, 6],
                                    },
                                }"
                            />
                        </template>
                    </Dialog>
                    <Button
                        label="Expand"
                        class="w-fit"
                        variant="outline"
                        size="sm"
                        @click="inExpandedDescription = true"
                    />
                </div>
            </div>
        </div>
    </div>
</template>
