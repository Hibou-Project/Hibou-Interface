<template>
  <div class="flex min-h-0 flex-1 flex-col">
    <div class="flex min-h-0 flex-1 gap-3 p-3">
      <div class="flex min-h-0 min-w-0 flex-1 flex-col">
        <DashboardVideoPanel />
      </div>
      <div class="flex min-h-0 min-w-0 flex-1 flex-col">
        <DashboardMapPanel />
      </div>
    </div>
    <DashboardSystemStatus />
  </div>
</template>

<script setup lang="ts">
definePageMeta({
  middleware: ['auth'],
})
</script>
