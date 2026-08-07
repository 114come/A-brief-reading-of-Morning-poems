<script setup lang="ts">
import { computed, nextTick, ref, watch } from 'vue'
import { Volume2 } from 'lucide-vue-next'
import { useTts } from '@/composables/useTts'
import type { TestQuestion } from '@/types'

const props = defineProps<{
  question: TestQuestion
}>()

const emit = defineEmits<{
  (e: 'answer', correct: boolean, userAnswer: string, usedHint: boolean): void
}>()

const { speakUS } = useTts()
const input = ref('')
const inputEl = ref<HTMLInputElement | null>(null)
const hintUsed = ref(false)
const submitted = ref(false)

const normalized = computed(() => input.value.trim().toLowerCase())

/** 题型D 遮蔽词：把 _ 补成当前已输入的部分展示 */
const maskedDisplay = computed(() => {
  if (props.question.type !== 'd') return ''
  const mask = props.question.mask
  let idx = 0
  return mask.replace(/_/g, () => {
    const ch = normalized.value[idx] ?? '_'
    idx += 1
    return ch
  })
})

/** 题型E：例句挖空 —— 用空格框替换目标词 */
const blankedExample = computed(() => {
  if (props.question.type !== 'e' || !props.question.example_en) return ''
  const re = new RegExp(`\\b${props.question.word}\\b`, 'gi')
  return props.question.example_en.replace(re, '_____')
})

function useHint(): void {
  if (hintUsed.value || submitted.value) return
  hintUsed.value = true
  // 填空D：补一个缺失字母
  if (props.question.type === 'd') {
    const mask = props.question.mask
    const target = props.question.answer
    let idx = 0
    for (let i = 0; i < mask.length; i++) {
      if (mask[i] === '_') {
        if (!normalized.value[idx]) {
          // 找这个位置对应的答案字母
          input.value = (input.value + target[i]).slice(0, target.length)
          break
        }
        idx++
      }
    }
  }
  // 填空E：无额外操作（提示按钮展示完整例句，在下方）
}

function check(): void {
  if (submitted.value) return
  submitted.value = true
  emit('answer', normalized.value === props.question.answer, input.value.trim(), hintUsed.value)
}

function onKeydown(e: KeyboardEvent): void {
  // Enter 提交
  if (e.key === 'Enter') {
    e.preventDefault()
    check()
  }
}

function focusNext(): void {
  void nextTick(() => inputEl.value?.focus())
}

watch(
  () => props.question.word_id,
  () => {
    input.value = ''
    hintUsed.value = false
    submitted.value = false
    void nextTick(() => inputEl.value?.focus())
  },
)

defineExpose({ focusNext })

// 首次聚焦
void nextTick(() => inputEl.value?.focus())
</script>

<template>
  <div class="fill-question">
    <!-- 题型D：单词填空 -->
    <template v-if="question.type === 'd'">
      <div class="q-def">{{ question.definition }}</div>
      <div class="q-meta">
        <span v-if="question.phonetic" class="q-phonetic">{{ question.phonetic }}</span>
        <button class="audio-btn" type="button" @click="speakUS(question.word)"><Volume2 :size="14" :stroke-width="2" />发音</button>
      </div>
      <div class="q-blank-word">{{ maskedDisplay || question.mask }}</div>
      <p class="q-tip">补全单词（首尾字母已给出）</p>
    </template>

    <!-- 题型E：例句填空 -->
    <template v-else>
      <div class="q-example-cn">{{ question.example_cn }}</div>
      <div class="q-example-en">{{ blankedExample }}</div>
      <div class="q-meta">
        <button class="audio-btn" type="button" @click="speakUS(question.example_en || question.word)"><Volume2 :size="14" :stroke-width="2" />播放例句</button>
        <button v-if="hintUsed" class="audio-btn hint-shown" type="button" @click="speakUS(question.word)"><Volume2 :size="14" :stroke-width="2" />单词发音</button>
      </div>
      <p v-if="hintUsed" class="q-full-example">完整例句：{{ question.example_en }}</p>
      <p class="q-tip">填入句中缺失的单词</p>
    </template>

    <!-- 输入区 -->
    <div class="q-input-row">
      <input
        ref="inputEl"
        v-model="input"
        class="input fill-input"
        type="text"
        placeholder="输入英文单词"
        autocomplete="off"
        autocapitalize="off"
        spellcheck="false"
        :disabled="submitted"
        @keydown="onKeydown"
      />
    </div>

    <div class="q-actions">
      <button class="btn btn-ghost btn-sm" type="button" :disabled="hintUsed || submitted" @click="useHint">
        {{ hintUsed ? '已使用提示' : '提示（1次）' }}
      </button>
      <button class="btn btn-primary btn-sm" type="button" :disabled="submitted" @click="check">
        提交
      </button>
      <span class="q-key-hint">回车提交 · Tab 下一题</span>
    </div>
  </div>
</template>

<style scoped>
.fill-question {
  max-width: 620px;
  margin: 0 auto;
  padding: 32px 40px;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-sm);
  text-align: center;
}

.q-def {
  font-size: 22px;
  font-weight: 700;
  color: var(--text);
}

.q-meta {
  display: flex;
  gap: 10px;
  justify-content: center;
  align-items: center;
  margin-top: 10px;
}

.q-phonetic {
  font-size: 15px;
  color: var(--text-2);
}

.audio-btn {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 6px 14px;
  border: 1px solid var(--border-2);
  border-radius: 999px;
  background: var(--surface);
  color: var(--text);
  font-size: 13px;
}

.audio-btn:hover {
  border-color: var(--primary);
  color: var(--primary);
}

.q-blank-word {
  margin-top: 24px;
  font-size: 40px;
  font-weight: 800;
  letter-spacing: 6px;
  color: var(--primary);
  font-family: 'Courier New', monospace;
}

.q-example-cn {
  font-size: 17px;
  font-weight: 600;
  color: var(--text);
  line-height: 1.7;
}

.q-example-en {
  margin-top: 14px;
  font-size: 20px;
  font-weight: 600;
  color: var(--primary);
  line-height: 1.8;
}

.q-full-example {
  margin-top: 10px;
  font-size: 14px;
  color: var(--text-2);
  background: var(--surface-2);
  padding: 8px 14px;
  border-radius: 8px;
}

.q-tip {
  margin-top: 8px;
  font-size: 13px;
  color: var(--text-3);
}

.q-input-row {
  margin-top: 20px;
}

.fill-input {
  text-align: center;
  font-size: 20px;
  font-weight: 600;
  letter-spacing: 2px;
  max-width: 320px;
  margin: 0 auto;
  font-family: 'Courier New', monospace;
}

.q-actions {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  margin-top: 18px;
}

.q-key-hint {
  font-size: 12px;
  color: var(--text-3);
  margin-left: 8px;
}
</style>
