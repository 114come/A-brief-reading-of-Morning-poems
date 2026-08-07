<script setup lang="ts">
import { onMounted } from 'vue'
import { Sparkles } from 'lucide-vue-next'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useDailySummaryStore } from '@/stores/dailySummary'

const auth = useAuthStore()
const store = useDailySummaryStore()
const router = useRouter()

async function click(): Promise<void> {
  await store.generate()
  router.push('/study-center?tab=summary')
}

onMounted(() => {
  store.refreshHasActivity()
})
</script>

<template>
  <button
    v-if="auth.isLoggedIn && store.hasActivityToday"
    class="float-btn"
    type="button"
    @click="click"
  >
    <Sparkles :size="18" :stroke-width="1.8" />
    <span class="float-text">生成今日 AI 总结</span>
  </button>
</template>

<style scoped>
.float-btn {
  position: fixed;
  right: 28px;
  bottom: 32px;
  z-index: 900;
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 20px;
  border: none;
  border-radius: 999px;
  background: var(--brand-gradient);
  color: #fff;
  font-size: 14px;
  font-weight: 600;
  box-shadow: 0 8px 24px var(--primary-soft);
  transition: transform 0.2s ease, box-shadow 0.2s ease;
}

.float-btn:hover {
  transform: translateY(-2px);
  box-shadow: 0 12px 32px var(--primary-soft);
}
</style>
