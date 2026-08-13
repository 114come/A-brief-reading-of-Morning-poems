<script setup lang="ts">
import { ref } from 'vue'
import { PartyPopper, X } from 'lucide-vue-next'

const visible = ref(false)
const title = ref('')
const desc = ref('')

function show(t: string, d: string): void {
  title.value = t
  desc.value = d
  visible.value = true
}

function close(): void {
  visible.value = false
}

defineExpose({ show })
</script>

<template>
  <transition name="modal">
    <div v-if="visible" class="modal-mask" @click.self="close">
      <div class="celebration">
        <button class="close" type="button" aria-label="关闭" @click="close">
          <X :size="18" :stroke-width="1.8" />
        </button>
        <div class="cel-icon">
          <PartyPopper :size="30" :stroke-width="1.6" />
        </div>
        <h2 class="cel-title">{{ title }}</h2>
        <p class="cel-desc">{{ desc }}</p>
        <button class="btn btn-primary" type="button" @click="close">收下这份鼓励</button>
      </div>
    </div>
  </transition>
</template>

<style scoped>
.celebration {
  position: relative;
  width: 360px;
  max-width: calc(100vw - 40px);
  padding: 40px 32px 32px;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius-xl);
  box-shadow: var(--shadow-lg);
  text-align: center;
  animation: pop 0.4s var(--ease);
  overflow: hidden;
}
.celebration::before {
  content: '';
  position: absolute;
  inset: 0;
  background: var(--sunrise-glow);
  pointer-events: none;
}
@keyframes pop {
  from {
    transform: scale(0.86) translateY(16px);
    opacity: 0;
  }
  to {
    transform: scale(1) translateY(0);
    opacity: 1;
  }
}
.close {
  position: absolute;
  top: 14px;
  right: 14px;
  border: none;
  background: transparent;
  color: var(--text-3);
}
.cel-icon {
  width: 64px;
  height: 64px;
  margin: 0 auto 16px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  background: var(--brand-gradient);
  color: #fff;
  box-shadow: 0 8px 24px var(--sun-soft);
}
.cel-title {
  font-family: var(--font-display);
  font-size: 22px;
  font-weight: 700;
  margin-bottom: 8px;
}
.cel-desc {
  color: var(--text-2);
  margin-bottom: 24px;
}
.modal-enter-active,
.modal-leave-active {
  transition: opacity 0.25s ease;
}
.modal-enter-from,
.modal-leave-to {
  opacity: 0;
}
</style>
