<template>
  <div class="max-h-[45vh] shrink-0 overflow-y-auto border-t border-border">
    <div class="p-4">
      <div class="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Card v-for="component in components" :key="component.id">
          <CardHeader>
            <CardTitle class="flex justify-between">
              {{ component.name }}
              <NuxtLink v-if="component.link" :href="component.link" target="_blank" class="ml-2">
                <ExternalLink class="size-4" />
              </NuxtLink>
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div v-for="subcomponent in component.subcomponents" :key="subcomponent.id">
              <div class="flex items-center justify-between">
                <div class="flex items-center gap-2">
                  {{ subcomponent.name }}
                  <div
                    class="size-2 rounded-full"
                    :class="subcomponent.status ? 'bg-green-500' : 'bg-red-500'"
                  ></div>
                </div>
                <div class="text-sm text-muted-foreground">
                  {{ subcomponent.status ? 'Online' : 'Offline' }}
                </div>
              </div>
            </div>
            <div v-if="component.subcomponents.length === 0">
              <div class="flex items-center justify-between">
                <div
                  class="size-2 rounded-full"
                  :class="component.status ? 'bg-green-500' : 'bg-red-500'"
                ></div>
                <div class="text-sm text-muted-foreground">
                  {{ component.status ? 'Online' : 'Offline' }}
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle class="flex justify-between"> Acoustic Detections </CardTitle>
          </CardHeader>
          <CardContent class="grid grid-cols-4 gap-2">
            <div v-for="(detection, index) in acousticDetectionsDemo" :key="index">
              <div class="flex items-center gap-2">
                <span>Mic {{ index + 1 }}</span>
                <div
                  class="size-2 rounded-full"
                  :class="detection ? 'bg-green-500' : 'bg-red-500'"
                ></div>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ExternalLink } from 'lucide-vue-next'
import type { IPCEvent } from '~/types/ipc'

const ACTIVE_RESET_MS = 3000

interface SubcomponentItem {
  id: string
  name: string
  status: boolean
}

interface ComponentItem {
  id: string
  name: string
  link?: string
  status: boolean
  subcomponents: SubcomponentItem[]
}

const componentsData: ComponentItem[] = [
  {
    id: 'worker',
    name: 'Server',
    status: false,
    subcomponents: [
      { id: 'audio', name: 'Audio', status: false },
      { id: 'vision', name: 'Vision', status: false },
      { id: 'decision', name: 'Decision', status: false },
    ],
  },
  {
    id: 'preamplifier',
    name: 'Preamplifier Yamaha Tio',
    status: false,
    subcomponents: [],
  },
  {
    id: 'ptz_camera',
    name: 'PTZ Camera',
    link: 'http://192.168.250.30',
    status: false,
    subcomponents: [],
  },
]

const components = ref<ComponentItem[]>(
  componentsData.map((c) => ({
    ...c,
    subcomponents: c.subcomponents.map((s) => ({ ...s })),
  }))
)

const statusResetTimers = new Map<string, ReturnType<typeof setTimeout>>()

function clearStatusTimer(key: string) {
  const t = statusResetTimers.get(key)
  if (t !== undefined) {
    clearTimeout(t)
    statusResetTimers.delete(key)
  }
}

function scheduleStatusReset(key: string, setOffline: () => void) {
  clearStatusTimer(key)
  statusResetTimers.set(
    key,
    setTimeout(() => {
      setOffline()
      statusResetTimers.delete(key)
    }, ACTIVE_RESET_MS)
  )
}

function applySystemStatusPayload(payload: string) {
  const segments = payload.split(':')
  const state = segments[segments.length - 1]
  if (state !== 'active') return

  const list = components.value

  if (segments.length === 2) {
    const compId = segments[0]
    if (!compId) return
    const component = list.find((c) => c.id === compId)
    if (!component) return
    component.status = true
    scheduleStatusReset(compId, () => {
      const c = components.value.find((x) => x.id === compId)
      if (c) c.status = false
    })
    return
  }

  if (segments.length === 3) {
    const compId = segments[0]
    const subId = segments[1]
    if (!compId || !subId) return
    const component = list.find((c) => c.id === compId)
    const sub = component?.subcomponents.find((s) => s.id === subId)
    if (!sub) return
    sub.status = true
    const key = `${compId}:${subId}`
    scheduleStatusReset(key, () => {
      const c = components.value.find((x) => x.id === compId)
      const sc = c?.subcomponents.find((s) => s.id === subId)
      if (sc) sc.status = false
    })
  }
}

const acousticDetections = ref<number[]>([])
const acousticDetectionsDemo = computed(() => {
  return acousticDetections.value
})

const { addSubscriber } = useIPC()

addSubscriber((event: IPCEvent) => {
  const parts = event.data.split(' ')
  const payload = parts.slice(1).join(' ')
  if (!payload) return
  applySystemStatusPayload(payload)
}, 'system_status')

addSubscriber((event: IPCEvent) => {
  const detections = event.data.split(',').map(Number)
  acousticDetections.value = detections
}, 'acoustic_detection')

onUnmounted(() => {
  for (const t of statusResetTimers.values()) clearTimeout(t)
  statusResetTimers.clear()
})
</script>
