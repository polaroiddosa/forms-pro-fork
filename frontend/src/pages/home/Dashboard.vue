<template>
    <div class="flex flex-col gap-4 w-full overflow-y-auto">
        <Breadcrumbs :items="breadcrumbItems" />
        <div class="flex flex-col gap-2">
            <h2 class="text-3xl font-bold">My forms</h2>
            <p class="text-base">Create a form, then share its link</p>
        </div>
        <Button class="w-fit" variant="solid" iconLeft="plus" @click="handleCreateDraftForm">
            New form
        </Button>
        <div class="flex flex-col gap-2">
            <h3 class="font-medium">Your forms</h3>
            <p class="text-sm" v-if="teamForms.loading">Loading...</p>
            <p class="text-sm" v-else-if="!teamForms.data || teamForms.data.length === 0">
                No forms created yet
            </p>
            <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4" v-else>
                <div v-for="form in teamForms.data" :key="form.name">
                    <FormPreviewCard :form="form" />
                </div>
            </div>
        </div>
    </div>
</template>

<script setup lang="ts">
import { useRouter } from "vue-router";
import { ref, watch } from "vue";
import { toast } from "vue-sonner";
import { useUser } from "@/stores/user";
import { createResource, Breadcrumbs } from "frappe-ui";
import { createNewForm } from "@/utils/form_generator";
import FormPreviewCard from "@/components/dashboard/FormPreviewCard.vue";
const router = useRouter();
const user = useUser();

const breadcrumbItems = ref([{ label: "My forms" }]);

const handleCreateDraftForm = async () => {
    if (!user.currentTeam?.name) {
        toast.error("Error occured while creating form. User has no default team.");
        return;
    }
    const data = await createNewForm(user.currentTeam.name);
    router.push({
        name: "Edit Form",
        params: {
            id: data.form_document,
        },
    });
};

const teamForms = createResource({
    url: "forms_pro.api.team.get_team_forms",
    makeParams() {
        return {
            team_id: user.currentTeam?.name,
        };
    },
    loading: true,
    cache: "teamForms",
});

watch(
    () => user.currentTeam,
    (currentTeam) => {
        if (currentTeam) {
            teamForms.fetch();
        }
    },
    { immediate: true }
);
</script>
