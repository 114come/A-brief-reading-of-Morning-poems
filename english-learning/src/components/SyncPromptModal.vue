<script setup lang="ts">
import { ref } from 'vue'
import { CloudUpload } from 'lucide-vue-next'
import { useAuthStore } from '@/stores/auth'
import { useSrsStore } from '@/stores/srs'
import { useUiStore } from '@/stores/ui'

const ui = useUiStore()
const srs = useSrsStore()
const auth = useAuthStore()

const syncing = ref(false)

async function doSync(): Promise<void> {
  if (syncing.value) return
  syncing.value = true
  try {
    await srs.init()
    await srs.syncToCloud()
    ui.closeSyncPrompt()
  } finally {
    syncing.value = false
  }
}

function skip(): void {
  ui.closeSyncPrompt()
}
</script>

<template>
  <Teleport to="body">
    <transition name="modal">
      <div v-if="ui.syncPromptOpen" class="modal-mask" @click.self="skip">
        <div class="modal-box">
          <div class="empty-icon"><CloudUpload :size="28" :stroke-width="1.6" /></div>
          <div class="modal-title">检测到本地学习数据</div>
          <p class="modal-desc">
            你作为游客学习过 {{ auth.user?.nickname || auth.user?.username }}，是否将本地进度同步到云端？同步后换设备也不丢失。
          </p>
          <div class="modal-actions">
            <button class="btn btn-ghost" type="button" @click="skip">暂不同步</button>
            <button class="btn btn-primary" type="button" :disabled="syncing" @click="doSync">
              {{ syncing ? '同步中…' : '同步到云端' }}
            </button>
          </div>
        </div>
      </div>
    </transition>
  </Teleport>
</template>

<style scoped>
.modal-enter-active,
.modal-leave-active {
  transition: opacity 0.2s ease;
}

.modal-enter-from,
.modal-leave-to {
  opacity: 0;
}
</style>
