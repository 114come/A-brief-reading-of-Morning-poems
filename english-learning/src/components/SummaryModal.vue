<script setup lang="ts">
import { Sparkles } from 'lucide-vue-next'
import { useAuthStore } from '@/stores/auth'
import type { CompleteResult } from '@/types'

defineProps<{
  result: CompleteResult
  isGuest: boolean
  /** 词库中还有未学单词，可继续学习 */
  canContinue: boolean
}>()

const emit = defineEmits<{
  (e: 'close'): void
  (e: 'continue'): void
}>()
const auth = useAuthStore()
</script>

<template>
  <Teleport to="body">
    <div class="modal-mask" @click.self="emit('close')">
      <div class="modal-box summary-box">
        <div class="empty-icon"><Sparkles :size="28" :stroke-width="1.6" /></div>
        <div class="modal-title" style="text-align: center">今日学习完成</div>

        <div class="summary-grid">
          <div class="sum-item">
            <div class="sum-num">{{ result.summary.total_studied }}</div>
            <div class="sum-label">累计背诵</div>
          </div>
          <div class="sum-item">
            <div class="sum-num" style="color: var(--danger)">{{ result.summary.wordbook_count }}</div>
            <div class="sum-label">生词总数</div>
          </div>
          <div class="sum-item">
            <div class="sum-num" style="color: var(--success)">{{ result.checkin.streak_days }}</div>
            <div class="sum-label">连续打卡</div>
          </div>
          <div class="sum-item">
            <div class="sum-num">{{ result.summary.mastered_count }}</div>
            <div class="sum-label">已掌握</div>
          </div>
        </div>

        <p class="summary-tip">明天将推送复习单词，继续保持！</p>

        <div v-if="isGuest" class="summary-guest">
          游客模式已保存本地打卡。登录可同步到云端，换设备不丢失。
        </div>

        <div class="modal-actions" style="justify-content: center">
          <button
            v-if="canContinue"
            class="btn btn-primary"
            type="button"
            @click="emit('continue')"
          >
            继续学习 →
          </button>
          <button v-if="isGuest" class="btn btn-ghost" type="button" @click="auth.requireAuth(); emit('close')">
            登录同步
          </button>
          <button
            class="btn"
            :class="canContinue ? 'btn-ghost' : 'btn-primary'"
            type="button"
            @click="emit('close')"
          >
            今日到此为止
          </button>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<style scoped>
.summary-box {
  text-align: center;
}

.summary-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 10px;
  margin: 20px 0;
}

.sum-item {
  padding: 12px 6px;
  background: var(--surface-2);
  border-radius: 10px;
}

.sum-num {
  font-size: 24px;
  font-weight: 800;
  color: var(--primary);
}

.sum-label {
  font-size: 12px;
  color: var(--text-2);
  margin-top: 2px;
}

.summary-tip {
  font-size: 13px;
  color: var(--text-2);
}

.summary-guest {
  margin-top: 12px;
  padding: 10px;
  background: var(--primary-soft);
  border-radius: 10px;
  font-size: 12px;
  color: var(--text-2);
}
</style>
