import { defineStore } from 'pinia'
import { ref } from 'vue'

/**
 * 新手引导弹窗状态：首次进入背单词/切换新词书时打开，不可跳过。
 */
export const useOnboardingStore = defineStore('onboarding', () => {
  const isOpen = ref(false)
  /** 引导要初始化的词书（默认用设置里的当前词书） */
  const pendingBookId = ref<number | null>(null)

  function open(bookId?: number): void {
    pendingBookId.value = bookId ?? null
    isOpen.value = true
  }

  function close(): void {
    isOpen.value = false
  }

  return { isOpen, pendingBookId, open, close }
})
