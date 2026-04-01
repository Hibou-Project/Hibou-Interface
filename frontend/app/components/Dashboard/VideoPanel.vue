<template>
  <div
    class="relative flex h-full min-h-0 w-full flex-col overflow-hidden rounded-lg border border-border bg-black/80"
  >
    <div
      class="absolute right-4 top-4 z-10 flex gap-1 rounded-md border border-border/80 bg-background/90 p-0.5 shadow-sm backdrop-blur-sm"
    >
      <button
        type="button"
        class="rounded px-2 py-1 text-xs font-medium transition-colors"
        :class="
          activeChannel === VISION_CH_RAW
            ? 'bg-primary text-primary-foreground'
            : 'text-muted-foreground hover:bg-muted hover:text-foreground'
        "
        @click="activeChannel = VISION_CH_RAW"
      >
        {{ $t('dashboard.videoChannelRaw') }}
      </button>
      <button
        type="button"
        class="rounded px-2 py-1 text-xs font-medium transition-colors"
        :class="
          activeChannel === VISION_CH_ANNOTATED
            ? 'bg-primary text-primary-foreground'
            : 'text-muted-foreground hover:bg-muted hover:text-foreground'
        "
        @click="activeChannel = VISION_CH_ANNOTATED"
      >
        {{ $t('dashboard.videoChannelAnnotated') }}
      </button>
    </div>
    <img
      v-show="displaySrc && !showVideoOverlay"
      :key="displayKey"
      :src="displaySrc ?? undefined"
      class="h-full w-full object-contain"
      alt=""
      referrerpolicy="no-referrer"
      @error="streamError = true"
      @load="streamError = false"
    />
    <div
      v-if="showVideoOverlay"
      class="absolute inset-0 flex flex-col items-center justify-center bg-muted/30 p-6 text-center"
    >
      <p class="text-sm font-medium text-foreground">
        {{ $t('dashboard.videoTitle') }}
      </p>
      <p class="mt-1 max-w-sm text-sm text-primary">
        <template v-if="streamError">
          {{ $t('dashboard.videoStreamFailed') }}
        </template>
        <template v-else-if="activeChannel === VISION_CH_RAW && !ptzMjpegUrl">
          {{ $t('dashboard.videoNeedToken') }}
        </template>
        <template v-else>
          {{ $t('dashboard.videoWaitingAnnotated') }}
        </template>
      </p>
    </div>
  </div>
</template>

<script setup lang="ts">
const {
  VISION_CH_RAW,
  VISION_CH_ANNOTATED,
  activeChannel,
  streamError,
  ptzMjpegUrl,
  displaySrc,
  displayKey,
  showVideoOverlay,
} = useVisionVideoPanel()
</script>
