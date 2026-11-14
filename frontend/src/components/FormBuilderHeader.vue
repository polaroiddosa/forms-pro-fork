<script setup lang="ts">
import { Badge, Button, Popover, Tooltip, type ButtonProps } from "frappe-ui";
import { TextMorph } from "torph/vue";
import { ChevronDown, CloudCheck, Link as LinkIcon, Check, CloudOff } from "@lucide/vue";
import { useEditForm } from "@/stores/editForm";
import { useRouter } from "vue-router";
import { computed, nextTick, onMounted, ref, watch } from "vue";
import Logo from "@/assets/Logo.vue";

const router = useRouter();
const editFormStore = useEditForm();

const SUBMISSION_ROUTE_NAME = "Form Submission Page";

type ActionConfig = {
    label: string;
    iconLeft: string;
    variant: ButtonProps["variant"];
    theme: ButtonProps["theme"];
    handler: () => unknown;
};

function computeConfig(): ActionConfig {
    if (editFormStore.isUnsaved && editFormStore.isPublished)
        return {
            label: "Save and publish",
            iconLeft: "globe",
            variant: "solid",
            theme: "gray",
            handler: editFormStore.saveAndPublish,
        };
    if (editFormStore.isUnsaved)
        return {
            label: "Save",
            iconLeft: "",
            variant: "solid",
            theme: "gray",
            handler: editFormStore.save,
        };
    if (editFormStore.isPublished)
        return {
            label: "Unpublish",
            iconLeft: "",
            variant: "subtle",
            theme: "red",
            handler: editFormStore.togglePublish,
        };
    return {
        label: "Publish",
        iconLeft: "globe",
        variant: "solid",
        theme: "gray",
        handler: editFormStore.togglePublish,
    };
}

const frozenConfig = ref<ActionConfig | null>(null);
const buttonConfig = computed<ActionConfig>(() => frozenConfig.value ?? computeConfig());

watch(
    () => editFormStore.formResource,
    (r) => {
        if (!r) frozenConfig.value = null;
    }
);

// torph@0.0.9 TextMorph skips render when mounted with static text:
// MorphController.attach() only calls update() if lastText is set, and the
// text-prop watcher has no `immediate: true`. Mount with empty string, then
// assign post-mount so the watcher fires and populates the DOM.
const morphLabel = ref("");
onMounted(() => {
    morphLabel.value = buttonConfig.value.label;
});
watch(
    () => buttonConfig.value.label,
    (l) => {
        morphLabel.value = l;
    }
);

async function onAction() {
    if (frozenConfig.value) return;
    frozenConfig.value = computeConfig();
    try {
        await frozenConfig.value.handler();
        await nextTick();
    } catch {
        // save() rejects on duplicate fieldnames / no-changes; togglePublish surfaces errors via toast
    } finally {
        frozenConfig.value = null;
    }
}

// The public link visitors use: `${origin}/f/${route}` (path comes from the
// "Form Submission Page" route record so it follows router.ts).
const publicLink = computed(() => {
    const route = editFormStore.originalFormData?.route;
    if (!route) return "";
    const routeRecord = router.getRoutes().find((r) => r.name === SUBMISSION_ROUTE_NAME);
    if (!routeRecord) return "";
    // router.resolve() with a path string does not URL-encode "/" inside the route
    // (unlike a params object), so routes such as "s/something" stay intact.
    const path = routeRecord.path.replace(/:\w+\(.*?\)/, route);
    return `${window.location.origin}${router.resolve(path).href}`;
});

const copied = ref(false);
let copiedTimer: ReturnType<typeof setTimeout> | null = null;

async function copyText(text: string) {
    try {
        await navigator.clipboard.writeText(text);
        return true;
    } catch {
        // Clipboard API needs a secure context; fall back to a hidden textarea.
        const el = document.createElement("textarea");
        el.value = text;
        el.setAttribute("readonly", "");
        el.style.position = "fixed";
        el.style.opacity = "0";
        document.body.appendChild(el);
        el.select();
        let ok = false;
        try {
            ok = document.execCommand("copy");
        } catch {
            ok = false;
        }
        document.body.removeChild(el);
        return ok;
    }
}

async function copyLink() {
    if (!publicLink.value) return;
    if (await copyText(publicLink.value)) {
        copied.value = true;
        if (copiedTimer) clearTimeout(copiedTimer);
        copiedTimer = setTimeout(() => (copied.value = false), 2000);
    }
}
</script>
<template>
    <header
        class="form-builder-header flex justify-between items-center py-2 px-4 border-b h-[3rem]"
        data-form-builder-component="form-builder-header"
    >
        <Popover>
            <template #target="{ togglePopover }">
                <button class="flex items-center gap-1" @click="togglePopover">
                    <Logo />
                    <ChevronDown class="w-5 h-5" />
                </button>
            </template>
            <template #body-main>
                <div class="flex flex-col gap-2 bg-white rounded-lg p-2">
                    <Button
                        label="Go Back"
                        icon-left="arrow-left"
                        variant="ghost"
                        @click="
                            router.replace({
                                name: 'Manage Form',
                                params: {
                                    id: editFormStore.originalFormData?.name,
                                },
                            })
                        "
                    />
                </div>
            </template>
        </Popover>
        <div class="flex items-center gap-2 m-auto">
            <Badge
                v-if="editFormStore.isUnsaved"
                variant="subtle"
                label="Unsaved"
                theme="orange"
                size="sm"
            />
            <Tooltip
                v-else-if="editFormStore.isPublished"
                text="Form is published"
                placement="bottom"
            >
                <CloudCheck class="w-4 h-4 text-gray-500" />
            </Tooltip>
            <Tooltip v-else text="Form is not published" placement="bottom">
                <CloudOff class="w-4 h-4 text-gray-500" />
            </Tooltip>
            <h3 class="text-base font-medium text-gray-600 text-center">
                {{ editFormStore.originalFormData?.title || "Untitled Form" }}
            </h3>
            <div v-if="publicLink" class="flex items-center gap-1">
                <Tooltip :text="publicLink" placement="bottom">
                    <Button
                        variant="ghost"
                        :label="copied ? 'Copied' : 'Copy link'"
                        :aria-label="copied ? 'Copied' : 'Copy link'"
                        data-testid="copy-link"
                        @click="copyLink"
                    >
                        <template #prefix>
                            <Check v-if="copied" class="w-4 h-4 text-ink-green-3" />
                            <LinkIcon v-else class="w-4 h-4 text-gray-500" />
                        </template>
                    </Button>
                </Tooltip>
            </div>
        </div>
        <div class="flex items-center gap-2">
            <Button
                :aria-label="buttonConfig.label"
                :icon-left="buttonConfig.iconLeft"
                :variant="buttonConfig.variant"
                :theme="buttonConfig.theme"
                :loading="editFormStore.isSaving || editFormStore.isLoading"
                @click="onAction"
            >
                <TextMorph :text="morphLabel" />
            </Button>
        </div>
    </header>
</template>
