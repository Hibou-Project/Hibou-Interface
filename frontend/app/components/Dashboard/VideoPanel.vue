<template>
  <div
    class="relative flex h-full min-h-0 w-full flex-col overflow-hidden rounded-lg border border-border bg-black/80"
  >
    <img
      v-show="mjpegSrc && !streamError"
      :key="mjpegKey"
      :src="mjpegSrc ?? undefined"
      class="h-full w-full object-contain"
      alt=""
      referrerpolicy="no-referrer"
      @error="streamError = true"
      @load="streamError = false"
    />
    <div
      v-if="!mjpegSrc || streamError"
      class="absolute inset-0 flex flex-col items-center justify-center bg-muted/30 p-6 text-center"
    >
      <p class="text-sm font-medium text-foreground">
        {{ $t('dashboard.videoTitle') }}
      </p>
      <p class="mt-1 max-w-sm text-sm text-muted-foreground">
        <template v-if="!mjpegSrc">
          {{ $t('dashboard.videoNeedToken') }}
        </template>
        <template v-else>
          {{ $t('dashboard.videoStreamFailed') }}
        </template>
      </p>
    </div>
  </div>
</template>

<script setup lang="ts">
const userStore = useUserStore()
const config = useRuntimeConfig()

const streamError = ref(false)

const mjpegSrc = computed(() => {
  const token = userStore.accessToken
  if (!token) return null
  const base = String(config.public.apiBase ?? '').replace(/\/$/, '')
  return `${base}/video/ptz/mjpeg?token=${encodeURIComponent(token)}&channel=raw`
})

/** Bumps when the access token changes so the image refetches. */
const mjpegKey = computed(() => `${userStore.accessToken ?? ''}`)

watch(mjpegSrc, () => {
  streamError.value = false
})
</script>
