<script setup lang="ts">
const { isDark } = useAppTheme()

useHead({
  meta: [
    {
      name: 'color-scheme',
      content: computed(() => (isDark.value ? 'dark' : 'light')),
    },
  ],
})
</script>

<template>
  <NuxtLayout>
    <NuxtPage />
  </NuxtLayout>
</template>
