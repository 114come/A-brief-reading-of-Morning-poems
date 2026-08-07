<script setup lang="ts">
import { ref, watch } from 'vue'
import { Check, X } from 'lucide-vue-next'
import { lookupWord, collectReadingWord, setReadingBlacklist } from '@/api/english'
import { useAuthStore } from '@/stores/auth'
import { useUiStore } from '@/stores/ui'
import type { ReadingKeyword } from '@/types'

const props = defineProps<{
  /** 点击的单词 */
  word: string
  /** 文章关键词表（含释义），优先命中 */
  keywords: ReadingKeyword[]
  articleId: number
}>()

const emit = defineEmits<{
  (e: 'collected'): void
  (e: 'close'): void
}>()

const auth = useAuthStore()
const ui = useUiStore()

const loading = ref(false)
const phonetic = ref<string | null>(null)
const definition = ref('')
const pos = ref<string | null>(null)
const collecting = ref(false)
const blacklisting = ref(false)
const collected = ref(false)
const blacklisted = ref(false)

// 优先用文章关键词释义，否则请求词典
watch(
  () => props.word,
  async (w) => {
    if (!w) return
    const kw = props.keywords.find(
      (k) => k.word.toLowerCase() === w.toLowerCase(),
    )
    if (kw) {
      definition.value = kw.definition
      phonetic.value = null
      loading.value = false
      return
    }
    loading.value = true
    definition.value = ''
    phonetic.value = null
    try {
      const r = await lookupWord(w)
      definition.value = r.definition
      phonetic.value = r.phonetic
      pos.value = r.pos
    } catch {
      definition.value = '（词典中暂无释义，可收藏后学习）'
    } finally {
      loading.value = false
    }
  },
  { immediate: true },
)

async function collect(): Promise<void> {
  if (!auth.requireAuth()) return
  if (collected.value) return
  collecting.value = true
  try {
    const res = await collectReadingWord(props.articleId, props.word, 'lookup', definition.value)
    if (res.status === 'collected') {
      collected.value = true
      ui.showToast('已加入阅读生词本')
      emit('collected')
    } else if (res.status === 'skipped' && res.reason === 'blacklisted') {
      ui.showToast('该词已在黑名单')
    } else if (res.status === 'skipped' && res.reason === 'mastered') {
      collected.value = true
      ui.showToast('该词已掌握')
    }
  } catch (e) {
    ui.showToast((e as Error).message || '操作失败')
  } finally {
    collecting.value = false
  }
}

async function markKnown(): Promise<void> {
  if (!auth.requireAuth()) return
  blacklisting.value = true
  try {
    await setReadingBlacklist(props.word, true)
    blacklisted.value = true
    ui.showToast('已标记为熟词，后续不再收录')
    emit('collected')
  } catch (e) {
    ui.showToast((e as Error).message || '操作失败')
  } finally {
    blacklisting.value = false
  }
}
</script>

<template>
  <div class="lookup-pop">
    <div class="pop-head">
      <span class="pop-word">{{ word }}</span>
      <span v-if="phonetic" class="pop-phonetic">{{ phonetic }}</span>
      <span v-if="pos" class="pop-pos">{{ pos }}</span>
      <button class="pop-close" type="button" aria-label="关闭" @click="emit('close')"><X :size="16" :stroke-width="2" /></button>
    </div>
    <div v-if="loading" class="pop-def">查询中…</div>
    <div v-else class="pop-def">{{ definition }}</div>
    <div class="pop-actions">
      <button
        class="btn btn-primary btn-sm"
        type="button"
        :disabled="collecting || collected || blacklisted"
        @click="collect"
      >
        <template v-if="collected"><Check :size="14" :stroke-width="2.5" />已收录</template>
        <template v-else-if="blacklisted">已在黑名单</template>
        <template v-else>加入生词本</template>
      </button>
      <button
        class="btn btn-ghost btn-sm"
        type="button"
        :disabled="blacklisting || collected || blacklisted"
        @click="markKnown"
      >
        <template v-if="blacklisted"><Check :size="14" :stroke-width="2.5" />熟词</template>
        <template v-else>标记熟词</template>
      </button>
    </div>
  </div>
</template>

<style scoped>
.lookup-pop {
  position: fixed;
  z-index: 1100;
  width: 300px;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 12px;
  box-shadow: var(--shadow-lg);
  padding: 14px 16px;
}

.pop-head {
  display: flex;
  align-items: center;
  gap: 8px;
}

.pop-word {
  font-size: 18px;
  font-weight: 800;
  color: var(--primary);
}

.pop-phonetic {
  font-size: 13px;
  color: var(--text-2);
}

.pop-pos {
  font-size: 12px;
  color: var(--text-3);
}

.pop-close {
  margin-left: auto;
  border: none;
  background: none;
  color: var(--text-3);
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 2px;
  border-radius: 6px;
  transition: all 0.18s ease;
}

.pop-close:hover {
  color: var(--danger);
  background: var(--danger-soft);
}

.pop-def {
  margin-top: 8px;
  font-size: 14px;
  line-height: 1.7;
  color: var(--text);
}

.pop-actions {
  margin-top: 12px;
  display: flex;
  gap: 8px;
  justify-content: flex-end;
}
</style>
