<script setup lang="ts">
import { Lock } from 'lucide-vue-next'
import { useAuthStore } from '@/stores/auth'

export interface PageTab {
  key: string
  label: string
  /** 需要登录才能查看；游客点击时弹登录提示而不是切换 */
  requiresLogin?: boolean
}

const props = defineProps<{
  tabs: PageTab[]
  modelValue: string
}>()

const emit = defineEmits<{
  (e: 'update:modelValue', value: string): void
}>()

const auth = useAuthStore()

function select(tab: PageTab): void {
  // Tab 切换不是路由变化，游客拦截需在此处理
  if (tab.requiresLogin && !auth.isLoggedIn) {
    auth.requireAuth()
    return
  }
  emit('update:modelValue', tab.key)
}
</script>

<template>
  <div class="tabs">
    <button
      v-for="tab in props.tabs"
      :key="tab.key"
      type="button"
      class="tab-item"
      :class="{ active: tab.key === props.modelValue }"
      @click="select(tab)"
    >
      <Lock v-if="tab.requiresLogin && !auth.isLoggedIn" class="tab-lock" :size="12" :stroke-width="2" />
      {{ tab.label }}
    </button>
  </div>
</template>

<style scoped>
.tab-lock {
  vertical-align: -1px;
  margin-right: 4px;
  opacity: 0.7;
}
</style>
