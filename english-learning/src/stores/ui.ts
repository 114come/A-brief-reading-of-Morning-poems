import { defineStore } from 'pinia'
import { ref } from 'vue'
import router from '@/router'

/**
 * 全局 UI 状态：游客访问私有页面时的登录提示弹窗
 */
export const useUiStore = defineStore('ui', () => {
  const loginPromptOpen = ref(false)
  const loginRedirect = ref<string>('/home')

  const toastMessage = ref('')
  const toastVisible = ref(false)
  let toastTimer: ReturnType<typeof setTimeout> | null = null

  const syncPromptOpen = ref(false)

  function showToast(message: string, duration = 2200): void {
    toastMessage.value = message
    toastVisible.value = true
    if (toastTimer) clearTimeout(toastTimer)
    toastTimer = setTimeout(() => {
      toastVisible.value = false
    }, duration)
  }

  function openSyncPrompt(): void {
    syncPromptOpen.value = true
  }

  function closeSyncPrompt(): void {
    syncPromptOpen.value = false
  }

  function openLoginPrompt(redirect?: string): void {
    if (redirect) loginRedirect.value = redirect
    loginPromptOpen.value = true
  }

  function closeLoginPrompt(): void {
    loginPromptOpen.value = false
  }

  /** 点击「前往登录」：关闭弹窗并跳转登录页，带 redirect 参数 */
  function goLogin(): void {
    const target = loginRedirect.value
    closeLoginPrompt()
    router.push({ path: '/login', query: target && target !== '/home' ? { redirect: target } : {} })
  }

  return {
    loginPromptOpen,
    loginRedirect,
    toastMessage,
    toastVisible,
    syncPromptOpen,
    openLoginPrompt,
    closeLoginPrompt,
    goLogin,
    showToast,
    openSyncPrompt,
    closeSyncPrompt,
  }
})
