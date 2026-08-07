<script setup lang="ts">
import { onMounted } from 'vue'
import { Volume2 } from 'lucide-vue-next'
import { useTts } from '@/composables/useTts'
import type { TestQuestion } from '@/types'

const props = defineProps<{
  question: TestQuestion
  /** 听音题自动播放 */
  autoplay?: boolean
}>()

const emit = defineEmits<{
  (e: 'answer', correct: boolean): void
}>()

const { speakUS, speakUK } = useTts()

function choose(option: string): void {
  emit('answer', option === props.question.answer)
}

onMounted(() => {
  if (props.question.type === 'c' && props.autoplay) {
    setTimeout(() => speakUS(props.question.word), 300)
  }
})
</script>

<template>
  <div class="mc-question">
    <!-- 题型A：英译中 → 展示单词 -->
    <div v-if="question.type === 'a'" class="q-prompt">
      <div class="q-word">{{ question.word }}</div>
      <div class="q-phonetic">{{ question.phonetic }}</div>
      <div class="q-audio">
        <button class="audio-btn" type="button" @click="speakUS(question.word)"><Volume2 :size="14" :stroke-width="2" />美音</button>
        <button class="audio-btn" type="button" @click="speakUK(question.word)"><Volume2 :size="14" :stroke-width="2" />英音</button>
      </div>
      <div class="q-tip">选择正确的中文释义</div>
    </div>

    <!-- 题型B：中译英 → 展示释义 -->
    <div v-else-if="question.type === 'b'" class="q-prompt">
      <div class="q-def">{{ question.definition }}</div>
      <div v-if="question.pos" class="q-pos">{{ question.pos }}</div>
      <div class="q-tip">选择对应的英文单词</div>
    </div>

    <!-- 题型C：听音选义 → 隐藏单词，仅音频 -->
    <div v-else-if="question.type === 'c'" class="q-prompt">
      <div class="q-audio big">
        <button class="audio-btn" type="button" @click="speakUS(question.word)"><Volume2 :size="14" :stroke-width="2" />播放发音</button>
        <button class="audio-btn" type="button" @click="speakUK(question.word)"><Volume2 :size="14" :stroke-width="2" />英音</button>
      </div>
      <div class="q-tip">听发音，选择对应的中文释义</div>
    </div>

    <!-- 选项 -->
    <div class="q-options">
      <button
        v-for="(opt, i) in question.options"
        :key="i"
        type="button"
        class="option-btn"
        @click="choose(opt)"
      >
        <span class="opt-letter">{{ String.fromCharCode(65 + i) }}</span>
        <span class="opt-text">{{ opt }}</span>
      </button>
    </div>
  </div>
</template>

<style scoped>
.mc-question {
  max-width: 620px;
  margin: 0 auto;
  padding: 32px 40px;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-sm);
}

.q-prompt {
  text-align: center;
  margin-bottom: 24px;
}

.q-word {
  font-size: 40px;
  font-weight: 800;
  color: var(--primary);
}

.q-phonetic {
  font-size: 16px;
  color: var(--text-2);
  margin-top: 4px;
}

.q-def {
  font-size: 22px;
  font-weight: 700;
  color: var(--text);
}

.q-pos {
  margin-top: 6px;
  font-size: 13px;
  color: var(--text-3);
}

.q-audio {
  display: flex;
  gap: 10px;
  justify-content: center;
  margin-top: 12px;
}

.q-audio.big {
  margin-top: 40px;
}

.audio-btn {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 7px 16px;
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
}

.q-tip {
  margin-top: 10px;
  font-size: 13px;
  color: var(--text-3);
}

.q-options {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
}

.option-btn {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 14px 16px;
  border: 1px solid var(--border-2);
  border-radius: 10px;
  background: var(--surface);
  color: var(--text);
  font-size: 14px;
  text-align: left;
  transition: all 0.15s ease;
}

.option-btn:hover {
  border-color: var(--primary);
  background: var(--primary-soft);
}

.opt-letter {
  width: 24px;
  height: 24px;
  border-radius: 6px;
  background: var(--surface-2);
  color: var(--text-2);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 13px;
  font-weight: 700;
  flex-shrink: 0;
}

.opt-text {
  flex: 1;
  line-height: 1.5;
}
</style>
