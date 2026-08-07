<script setup lang="ts">
import { Moon, Sun } from 'lucide-vue-next'
import { useThemeStore } from '@/stores/theme'

const themeStore = useThemeStore()
</script>

<template>
  <button
    class="theme-toggle"
    :title="themeStore.isDark ? '切换到浅色模式' : '切换到深色模式'"
    @click="themeStore.toggle()"
  >
    <!-- 深色时显示太阳（点击切回浅色），浅色时显示月亮 -->
    <Sun v-if="themeStore.isDark" :size="18" :stroke-width="1.8" />
    <Moon v-else :size="18" :stroke-width="1.8" />
  </button>
</template>

<style scoped>
.theme-toggle {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  border-radius: 10px;
  border: 1px solid var(--border);
  background: var(--surface);
  color: var(--text-2);
  transition: all 0.18s ease;
}

.theme-toggle:hover {
  color: var(--primary);
  border-color: var(--primary);
  box-shadow: 0 2px 10px var(--primary-soft);
}
</style>
