<template>
  <div class="p-4">
    <div class="grid grid-cols-2 mt-2">
      <div>
        <h2 class="text-2xl font-bold pb-4">System Status</h2>
        <div class="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
          <Card v-for="status in systemStatus" :key="status.name">
            <CardHeader>
              <CardTitle class="flex justify-between">
                {{ status.name }}
                <NuxtLink v-if="status.link" :href="status.link" target="_blank" class="ml-2">
                  <ExternalLink class="size-4" />
                </NuxtLink>
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div class="flex items-center justify-between">
                <div class="flex items-center gap-2">
                  <div
                    class="size-2 rounded-full"
                    :class="status.status ? 'bg-green-500' : 'bg-red-500'"
                  ></div>
                </div>
                <div class="text-sm text-muted-foreground">
                  {{ status.status ? 'Online' : 'Offline' }}
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
    <Card class="w-xl p-4 mt-4">
      <h1>Test event</h1>
      <Input v-model="event" type="text" placeholder="Test event" />
      <Button @click="ws.send(event)">Send</Button>
    </Card>
  </div>
</template>

<script setup lang="ts">
import { ExternalLink } from 'lucide-vue-next'


definePageMeta({
  middleware: ['auth'],
})

const event = ref('')

const systemStatus = ref([
  {
    name: 'PTZ Camera',
    status: true,
    link: 'http://192.168.250.30',
  },
  {
    name: 'Yamaha Tio',
    status: false,
  },
  {
    name: 'Server',
    status: true,
  },
])

const ws = new WebSocket("ws://localhost:8000/events/ws")

ws.onmessage = (e) => {
    console.log(e)
}

console.log(ws)

</script>
