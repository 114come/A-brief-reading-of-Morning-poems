<script setup lang="ts">
import { onUnmounted, ref } from 'vue'
import { Sparkles } from 'lucide-vue-next'

const visible = ref(false)
const amount = ref(0)
const message = ref('')
let timer: ReturnType<typeof setTimeout> | null = null

function show(earned: number, msg: string): void {
  amount.value = earned
  message.value = msg
  visible.value = true
  if (timer) clearTimeout(timer)
  timer = setTimeout(() => (visible.value = false), 2600)
}

onUnmounted(() => {
  if (timer) clearTimeout(timer)
})

defineExpose({ show })
</script>

<template>
  <transition name="float">
    <div v-if="visible" class="point-toast">
      <Sparkles :size="16" :stroke-width="1.8" />
      <span class="pt-amount">+{{ amount }}</span>
      <span class="pt-msg">{{ message }}</span>
    </div>
  </transition>
</template>

<style scoped>
.point-toast {
  position: fixed;
  left: 50%;
  bottom: 120px;
  transform: translateX(-50%);
  z-index: 1100;
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 20px;
  border-radius: 999px;
  background: var(--text);
  color: var(--bg);
  font-size: 14px;
  box-shadow: var(--shadow-lg);
}
.pt-amount {
  color: var(--sun);
  font-weight: 700;
}
.float-enter-active,
.float-leave-active {
  transition: all 0.3s var(--ease);
}
.float-enter-from,
.float-leave-to {
  opacity: 0;
  transform: translateX(-50%) translateY(12px);
}
</style>
