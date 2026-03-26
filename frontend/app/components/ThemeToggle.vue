<template>
  <Button
    type="button"
    variant="ghost"
    size="icon"
    class="relative"
    :aria-pressed="isDark"
    :aria-label="t('theme.toggle')"
    @click="toggle()"
  >
    <Sun
      class="size-[1.15rem] scale-100 rotate-0 transition-all dark:-rotate-90 dark:scale-0"
    />
    <Moon
      class="absolute size-[1.15rem] scale-0 rotate-90 transition-all dark:rotate-0 dark:scale-100"
    />
    <span class="sr-only">{{ t('theme.toggle') }}</span>
  </Button>
</template>

<script setup lang="ts">
import { Moon, Sun } from 'lucide-vue-next'
import { Button } from '@/components/ui/button'

const { t } = useI18n()
const { isDark, toggle } = useAppTheme()
</script>
