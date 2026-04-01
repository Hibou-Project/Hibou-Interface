import { createSharedComposable, useWebSocket } from '@vueuse/core'
import type { IPCEvent } from '~/types/ipc'
import { eventsWebSocketUrl } from '~/utils/websocket'

const EVENTS_WS_PATH = '/events/ws'

type Subscriber = [(event: IPCEvent) => void, string]

const useSharedIPC = createSharedComposable(() => {
  const config = useRuntimeConfig()
  const userStore = useUserStore()
  const subscribers = ref<Subscriber[]>([])

  const url = computed(() => {
    const base = config.public.apiBase as string
    const token = userStore.accessToken
    if (!base?.trim() || !token) return ''
    return eventsWebSocketUrl(base, EVENTS_WS_PATH, token)
  })

  const ws = useWebSocket(url, {
    autoReconnect: {
      retries: Infinity,
      delay: 3000,
    },
    onConnected: () => console.log('connected'),
    onError: (ws, event) => console.error('WebSocket error', event),
    onMessage: (_ws, event) => {
      const msg: IPCEvent = { data: String(event.data) }
      subscribers.value.forEach((subscriber: Subscriber) => {
        const [callback, filter] = subscriber
        if (msg.data.startsWith(filter)) {
          callback(msg)
        }
      })
    },
  })

  const addSubscriber = (callback: (event: IPCEvent) => void, filter: string = '') => {
    subscribers.value.push([callback, filter])
  }

  return { ...ws, addSubscriber }
})

export function useIPC() {
  return useSharedIPC()
}
