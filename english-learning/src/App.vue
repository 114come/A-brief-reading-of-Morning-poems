<script setup lang="ts">
import { watch } from 'vue'
import { useRoute } from 'vue-router'
import AppHeader from '@/components/AppHeader.vue'
import AmbientMusicPlayer from '@/components/AmbientMusicPlayer.vue'
import LoginPromptModal from '@/components/LoginPromptModal.vue'
import SyncPromptModal from '@/components/SyncPromptModal.vue'
import DailySummaryFloatBtn from '@/components/DailySummaryFloatBtn.vue'
import { useUiStore } from '@/stores/ui'

const route = useRoute()
const ui = useUiStore()

// 路由切换回到顶部
watch(
  () => route.path,
  () => window.scrollTo({ top: 0 }),
)
</script>

<template>
  <AppHeader />
  <main class="page">
    <RouterView />
  </main>
  <LoginPromptModal />
  <SyncPromptModal />
  <DailySummaryFloatBtn />
  <AmbientMusicPlayer />

  <!-- 轻提示 -->
  <transition name="toast">
    <div v-if="ui.toastVisible" class="toast">{{ ui.toastMessage }}</div>
  </transition>
</template>

<style scoped>
.toast {
  position: fixed;
  left: 50%;
  bottom: 48px;
  transform: translateX(-50%);
  z-index: 1100;
  background: var(--text);
  color: var(--bg);
  padding: 10px 22px;
  border-radius: 999px;
  font-size: 14px;
  font-weight: 500;
  box-shadow: var(--shadow-lg);
}

.toast-enter-active,
.toast-leave-active {
  transition: opacity 0.25s ease, transform 0.25s ease;
}

.toast-enter-from,
.toast-leave-to {
  opacity: 0;
  transform: translateX(-50%) translateY(8px);
}
</style>
