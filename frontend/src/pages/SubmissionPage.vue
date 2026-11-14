<script setup lang="ts">
import { computed, ref } from "vue";
import { useRoute } from "vue-router";
import { call, createResource } from "frappe-ui";
import { ArrowRight } from "@lucide/vue";
import { useSubmissionForm } from "@/stores/submissionForm";
import FormHeader from "@/components/submission/FormHeader.vue";
import FormRenderer from "@/components/submission/FormRenderer.vue";
import StepIndicator from "@/components/submission/StepIndicator.vue";
import PreviousSubmissionSection from "@/components/submission/PreviousSubmissionSection.vue";
import SuccessSection from "@/components/submission/SuccessSection.vue";
import ConsentCheckbox from "@/components/fields/ConsentCheckbox.vue";
import PublicFooter from "@/components/fields/PublicFooter.vue";
import { MAX_FILES_PER_FORM, countAttachments } from "@/components/fields/attachment";
import { Fieldtype } from "@/types/formfield";
import Logo from "@/assets/Logo.vue";

const route = useRoute();
const submissionFormStore = useSubmissionForm();
submissionFormStore.initialize(route.params.route as string);

// Footer: source_url from the guest settings function (contract C7); empty/absent = no link.
const settings = createResource({
    url: "forms_pro.api.settings.get_website_settings",
    auto: true,
});
const sourceUrl = computed<string>(() => settings.data?.source_url || "");

// Consent (contract C1): wording from the form API, tick required before Submit.
const formData = computed<any>(() => submissionFormStore.formResource?.data);
const consentLabel = computed<string>(() => formData.value?.consent_label || "");
const consentText = computed<string>(() => formData.value?.consent_text || "");
const consentTicked = ref(false);
const submitting = ref(false);
const submitClicked = ref(false);

// Submit lives here (not in the store) so the consent value travels with the call.
async function submit() {
    submitClicked.value = true;
    const store = submissionFormStore;
    store.validateValues();
    if (store.errors.length > 0) return;
    const fields: any[] = formData.value?.fields || [];
    const files = countAttachments(
        fields.filter((f) => f.fieldtype === Fieldtype.ATTACH).map((f) => store.fields[f.fieldname])
    );
    if (files > MAX_FILES_PER_FORM) {
        store.errors = [`You can attach at most ${MAX_FILES_PER_FORM} files to one form.`];
        return;
    }
    if (!consentLabel.value || !consentTicked.value) {
        store.errors = ["Please tick the consent box so that we may contact you."];
        return;
    }
    submitting.value = true;
    try {
        await call("forms_pro.api.submission.submit_form_response", {
            form_id: formData.value.name,
            form_data: Object.entries(store.fields).map(([fieldname, value]) => ({
                fieldname,
                value,
            })),
            submission_status: "Submitted",
            consent: 1,
        });
        store.errors = [];
        store.inFormFillingState = false;
        store.inSuccessState = true;
    } catch (error: any) {
        store.errors = error?.messages?.length
            ? error.messages
            : ["Error while submitting form. Check the values and try again."];
    } finally {
        submitting.value = false;
    }
}
</script>
<template>
    <div class="ta-brand min-h-svh flex flex-col">
        <header class="max-w-screen-md w-full mx-auto px-4 pt-6 pb-2" data-public-header>
            <a href="/" aria-label="Transparent Academy"><Logo class="!h-14" /></a>
        </header>
        <main class="flex-1 px-4 py-4 space-y-6">
            <PreviousSubmissionSection v-if="submissionFormStore.userSubmissions" />
            <FormUnpublishedState
                v-if="!submissionFormStore.formIsPublished"
                class="form-container-simple"
            />
            <div v-else>
                <div class="my-4 max-w-screen-md mx-auto">
                    <StepIndicator
                        v-if="
                            submissionFormStore.isMultiStep &&
                            submissionFormStore.inFormFillingState
                        "
                        :steps="submissionFormStore.steps"
                        :currentIndex="submissionFormStore.currentStepIndex"
                        class="mb-4"
                        @go-to="submissionFormStore.goToStep"
                    />
                </div>
                <div class="form-container-simple !p-4 sm:!p-6 overflow-hidden mb-6">
                    <div class="space-y-4" v-if="submissionFormStore.inFormFillingState">
                        <FormHeader />
                        <FormRenderer :disabled="false">
                            <!-- Replaces the stock buttons: no draft button for visitors,
                                 consent tick above Submit, Submit blocked until ticked. -->
                            <template #actions>
                                <div class="flex flex-col gap-4 flex-1 min-w-0">
                                    <ConsentCheckbox
                                        v-if="submissionFormStore.isLastStep && consentLabel"
                                        v-model="consentTicked"
                                        :label="consentLabel"
                                        :text="consentText"
                                        :invalid="submitClicked && !consentTicked"
                                    />
                                    <p
                                        v-else-if="submissionFormStore.isLastStep"
                                        class="text-sm text-[#B3261E]"
                                        data-consent-missing
                                    >
                                        This form cannot be sent right now. Please try again later.
                                    </p>
                                    <div class="flex gap-2 flex-col-reverse sm:flex-row sm:justify-end">
                                        <Button
                                            v-if="
                                                submissionFormStore.isMultiStep &&
                                                !submissionFormStore.isFirstStep
                                            "
                                            class="w-full sm:w-auto"
                                            @click="submissionFormStore.prevStep"
                                        >
                                            Back
                                        </Button>
                                        <Button
                                            v-if="!submissionFormStore.isLastStep"
                                            variant="solid"
                                            class="w-full sm:w-auto"
                                            :loading="submissionFormStore.isLoading"
                                            @click="submissionFormStore.handleNextStep"
                                        >
                                            <span class="flex items-center gap-1.5">
                                                Next
                                                <ArrowRight class="w-3.5 h-3.5" :stroke-width="2.2" />
                                            </span>
                                        </Button>
                                        <Button
                                            v-else
                                            variant="solid"
                                            class="w-full sm:w-auto"
                                            :disabled="!consentLabel || !consentTicked"
                                            :loading="submitting"
                                            data-submit-button
                                            @click="submit"
                                        >
                                            Submit
                                        </Button>
                                    </div>
                                </div>
                            </template>
                        </FormRenderer>
                    </div>
                    <SuccessSection v-if="submissionFormStore.inSuccessState" />
                </div>
            </div>
        </main>
        <PublicFooter :sourceUrl="sourceUrl" />
    </div>
</template>
