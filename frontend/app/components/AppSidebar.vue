<template>
  <Sidebar collapsible="offcanvas" :variant="variant">
    <SidebarHeader class="flex flex-row items-center gap-1">
      <SidebarMenu class="min-w-0 flex-1">
        <SidebarMenuItem>
          <SidebarMenuButton as-child class="data-[slot=sidebar-menu-button]:!p-1.5">
            <NuxtLink :to="localePath('/dashboard')">
              <AudioLines class="!size-5" />
              <span class="text-base font-semibold">{{ $t('brand') }}</span>
            </NuxtLink>
          </SidebarMenuButton>
        </SidebarMenuItem>
      </SidebarMenu>
      <ThemeToggle />
    </SidebarHeader>
    <SidebarContent>
      <SidebarGroup>
        <SidebarGroupContent class="flex flex-col gap-2">
          <SidebarMenu>
            <SidebarMenuItem v-for="item in items" :key="item.title">
              <SidebarMenuButton :tooltip="item.title" as-child>
                <NuxtLink :to="item.href" class="flex items-center gap-2">
                  <component :is="item.icon" v-if="item.icon" class="size-4" />
                  <span>{{ item.title }}</span>
                </NuxtLink>
              </SidebarMenuButton>
            </SidebarMenuItem>
          </SidebarMenu>
        </SidebarGroupContent>
      </SidebarGroup>
    </SidebarContent>
    <SidebarFooter>
      <SidebarMenu>
        <SidebarMenuItem>
          <DropdownMenu>
            <DropdownMenuTrigger as-child>
              <SidebarMenuButton
                size="lg"
                class="data-[state=open]:bg-sidebar-accent data-[state=open]:text-sidebar-accent-foreground"
              >
                <template v-if="userStore.user">
                  <Avatar class="h-8 w-8 rounded-lg grayscale">
                    <AvatarFallback class="rounded-lg">
                      {{ userInitials }}
                    </AvatarFallback>
                  </Avatar>
                  <div class="grid flex-1 text-left text-sm leading-tight">
                    <span class="truncate font-medium">{{ userStore.user.identifier }}</span>
                  </div>
                </template>
              </SidebarMenuButton>
            </DropdownMenuTrigger>
            <DropdownMenuContent
              class="w-(--reka-dropdown-menu-trigger-width) min-w-56 rounded-lg"
              side="bottom"
              :side-offset="4"
            >
              <DropdownMenuLabel class="p-0 font-normal">
                <template v-if="userStore.user">
                  <div class="flex items-center gap-2 px-1 py-1.5 text-left text-sm">
                    <Avatar class="h-8 w-8 rounded-lg">
                      <AvatarFallback class="rounded-lg">
                        {{ userInitials }}
                      </AvatarFallback>
                    </Avatar>
                    <div class="grid flex-1 text-left text-sm leading-tight">
                      <span class="truncate font-medium">{{ userStore.user.identifier }}</span>
                    </div>
                  </div>
                </template>
              </DropdownMenuLabel>
              <DropdownMenuSeparator />
              <DropdownMenuItem @click="toggleLocale">
                <Languages class="size-4" />
                {{ localeSwitchLabel }}
              </DropdownMenuItem>
              <DropdownMenuItem @click="onLogout">
                <LogOut class="size-4" />
                {{ t('sidebar.logout') }}
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </SidebarMenuItem>
      </SidebarMenu>
    </SidebarFooter>
  </Sidebar>
</template>

<script setup lang="ts">
import { LayoutDashboard, AudioLines, Settings, LogOut, Languages } from 'lucide-vue-next'
import type { SidebarProps } from '@/components/ui/sidebar'
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarGroup,
  SidebarGroupContent,
} from '@/components/ui/sidebar'
import { useUserStore } from '../stores/user'

withDefaults(
  defineProps<{
    variant?: SidebarProps['variant']
  }>(),
  { variant: 'inset' }
)

const { t, locale, setLocale } = useI18n()
const localePath = useLocalePath()
const userStore = useUserStore()

const localeSwitchLabel = computed(() =>
  locale.value === 'en' ? t('sidebar.switchToFrench') : t('sidebar.switchToEnglish')
)

async function toggleLocale() {
  await setLocale(locale.value === 'en' ? 'fr' : 'en')
}

const items = computed(() => [
  {
    title: t('sidebar.dashboard'),
    icon: LayoutDashboard,
    href: localePath('/dashboard'),
  },
  {
    title: t('sidebar.settings'),
    icon: Settings,
    href: localePath('/settings'),
  },
])

const userInitials = computed(() => {
  const id = userStore.user?.identifier
  if (!id) return '?'
  return id.slice(0, 2).toUpperCase()
})

async function onLogout() {
  await userStore.logout()
  await navigateTo(localePath('/'))
}
</script>
