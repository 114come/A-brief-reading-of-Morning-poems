<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted } from 'vue'
import { Volume2 } from 'lucide-vue-next'
import type { Word } from '@/types'

const props = defineProps<{
  word: Word
  pronunciation?: 'us' | 'uk'
  autoplay?: boolean
}>()

const emit = defineEmits<{
  (e: 'answer', known: boolean): void
}>()

// Web Speech API 发音
const canSpeak = typeof window !== 'undefined' && 'speechSynthesis' in window

function speak(lang: string): void {
  if (!canSpeak) return
  window.speechSynthesis.cancel()
  const u = new SpeechSynthesisUtterance(props.word.word)
  u.lang = lang
  u.rate = 0.85
  window.speechSynthesis.speak(u)
}

function speakUS(): void {
  speak('en-US')
}

function speakUK(): void {
  speak('en-GB')
}

onMounted(() => {
  if (props.autoplay) speakUS()
})

onBeforeUnmount(() => {
  if (canSpeak) window.speechSynthesis.cancel()
})

const examples = computed(() => {
  const list: string[] = []
  if (props.word.example) list.push(props.word.example)
  if (props.word.example2) list.push(props.word.example2)
  return list
})
</script>

<template>
  <div class="word-card card card-pad">
    <div class="word-top">
      <div class="word-en">{{ word.word }}</div>
      <div v-if="word.phonetic" class="word-phonetic">{{ word.phonetic }}</div>
      <div class="audio-row">
        <button class="audio-btn" type="button" title="美式发音" @click="speakUS">
          <Volume2 :size="14" :stroke-width="2" />美
        </button>
        <button class="audio-btn" type="button" title="英式发音" @click="speakUK">
          <Volume2 :size="14" :stroke-width="2" />英
        </button>
      </div>
    </div>

    <div class="word-def">
      <span v-if="word.pos" class="word-pos">{{ word.pos }}</span>{{ word.definition }}
    </div>

    <div v-if="examples.length" class="examples">
      <div v-for="(ex, i) in examples" :key="i" class="example">
        <span class="ex-num">{{ i + 1 }}</span>{{ ex }}
      </div>
    </div>

    <div v-if="word.phrase" class="phrase">
      <span class="phrase-label">搭配</span>{{ word.phrase }}
    </div>

    <div class="answer-row">
      <button class="btn btn-primary answer-btn" type="button" @click="emit('answer', false)">不认识</button>
      <button class="btn btn-success answer-btn" type="button" @click="emit('answer', true)">认识</button>
    </div>
  </div>
</template>

<style scoped>
.word-card {
  max-width: 620px;
  margin: 0 auto;
  padding: 36px 40px;
  text-align: center;
}

.word-top {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
}

.word-en {
  font-size: 40px;
  font-weight: 800;
  letter-spacing: 1px;
  color: var(--primary);
}

.word-phonetic {
  font-size: 16px;
  color: var(--text-2);
}

.audio-row {
  display: flex;
  gap: 10px;
  margin-top: 8px;
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
  transition: all 0.18s ease;
}

.audio-btn:hover {
  border-color: var(--primary);
  color: var(--primary);
  box-shadow: 0 2px 10px var(--primary-soft);
}

.word-def {
  margin-top: 20px;
  font-size: 18px;
  font-weight: 600;
  color: var(--text);
}

.word-pos {
  display: inline-block;
  margin-right: 10px;
  padding: 2px 10px;
  border-radius: 6px;
  background: var(--primary-soft);
  color: var(--primary);
  font-size: 13px;
  font-weight: 700;
  vertical-align: middle;
}

.examples {
  margin-top: 18px;
  text-align: left;
}

.example {
  padding: 8px 12px;
  margin-top: 8px;
  background: var(--surface-2);
  border-radius: 10px;
  font-size: 14px;
  color: var(--text-2);
  line-height: 1.7;
}

.ex-num {
  display: inline-flex;
  width: 20px;
  height: 20px;
  border-radius: 6px;
  background: var(--primary-soft);
  color: var(--primary);
  font-size: 12px;
  font-weight: 700;
  align-items: center;
  justify-content: center;
  margin-right: 8px;
}

.phrase {
  margin-top: 14px;
  padding: 8px 14px;
  background: var(--success-soft);
  border-radius: 10px;
  font-size: 13px;
  color: var(--text-2);
}

.phrase-label {
  font-weight: 700;
  color: var(--success);
  margin-right: 8px;
}

.answer-row {
  display: flex;
  gap: 16px;
  margin-top: 28px;
  justify-content: center;
}

.answer-btn {
  flex: 1;
  max-width: 200px;
  height: 48px;
  font-size: 16px;
  font-weight: 700;
}

.btn-success {
  background: var(--success);
  color: #fff;
}

.btn-success:hover:not(:disabled) {
  background: var(--primary-2);
  box-shadow: 0 4px 14px var(--success-soft);
}
</style>
