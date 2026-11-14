<script setup lang="ts">
// Academy logo (brand pack, copied unchanged to public/brand/logo.svg). Replaces the
// "Forms Pro" text mark. Never recolour or redraw (brand rule).
const logoUrl = `${(import.meta as any).env?.BASE_URL ?? "/"}brand/logo.svg`;
</script>
<template>
    <img :src="logoUrl" alt="Transparent Academy" class="h-10 w-auto" />
</template>
