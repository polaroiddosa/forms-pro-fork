<script setup lang="ts">
// Footer of the public form page. The "Source code" link (licence slot, contract C7)
// appears only when the settings key source_url is non-empty.
defineProps<{ sourceUrl?: string | null }>();
</script>
<template>
    <footer class="max-w-screen-md mx-auto pt-4 pb-8 text-center text-sm text-ink-gray-6">
        <p data-footer-text>Enquiries are handled by Transparent Academy.</p>
        <p v-if="sourceUrl" class="mt-1 text-xs">
            <a
                :href="sourceUrl"
                target="_blank"
                rel="noopener noreferrer"
                class="underline"
                data-source-link
                >Source code</a
            >
        </p>
    </footer>
</template>
