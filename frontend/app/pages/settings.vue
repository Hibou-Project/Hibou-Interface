<template>
  <div class="p-8">
    <h1 class="text-xl font-semibold tracking-tight">
      {{ $t('settings.title') }}
    </h1>
  </div>
</template>

<script setup lang="ts">
definePageMeta({
  middleware: ['auth'],
})
</script>
