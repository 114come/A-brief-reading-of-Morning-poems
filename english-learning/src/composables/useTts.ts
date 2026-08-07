import { onBeforeUnmount } from 'vue'

/** Web Speech API 发音复用（题型C听音 + 单词卡 + 每日一读朗读） */
const canSpeak = typeof window !== 'undefined' && 'speechSynthesis' in window

/** 语速档：慢速/标准/快速（对应 rate 值） */
export const TTS_RATES = [
  { label: '慢速', rate: 0.7 },
  { label: '标准', rate: 1.0 },
  { label: '快速', rate: 1.3 },
] as const

export function useTts() {
  function speak(lang: string, text?: string, rate = 0.85): void {
    if (!canSpeak) return
    window.speechSynthesis.cancel()
    const u = new SpeechSynthesisUtterance(text ?? '')
    u.lang = lang
    u.rate = rate
    window.speechSynthesis.speak(u)
  }

  function speakUS(text?: string, rate?: number): void {
    speak('en-US', text, rate)
  }

  function speakUK(text?: string, rate?: number): void {
    speak('en-GB', text, rate)
  }

  function stop(): void {
    if (canSpeak) window.speechSynthesis.cancel()
  }

  onBeforeUnmount(stop)

  return { speak, speakUS, speakUK, stop, canSpeak }
}
