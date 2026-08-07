import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import router from '@/router'
import { getProfile, login as apiLogin, register as apiRegister } from '@/api/english'
import { ACCESS_KEY, REFRESH_KEY } from '@/api/http'
import { guestKeysExist } from '@/composables/srsStorage'
import { useUiStore } from './ui'
import type { UserProfile } from '@/types'

const USER_KEY = 'english_user'

function loadUser(): UserProfile | null {
  try {
    const raw = localStorage.getItem(USER_KEY)
    return raw ? (JSON.parse(raw) as UserProfile) : null
  } catch {
    return null
  }
}

export const useAuthStore = defineStore('auth', () => {
  const accessToken = ref<string>(localStorage.getItem(ACCESS_KEY) || '')
  const refreshToken = ref<string>(localStorage.getItem(REFRESH_KEY) || '')
  const user = ref<UserProfile | null>(loadUser())

  const isLoggedIn = computed<boolean>(() => Boolean(accessToken.value))

  function persist(): void {
    if (accessToken.value) localStorage.setItem(ACCESS_KEY, accessToken.value)
    else localStorage.removeItem(ACCESS_KEY)
    if (refreshToken.value) localStorage.setItem(REFRESH_KEY, refreshToken.value)
    else localStorage.removeItem(REFRESH_KEY)
    if (user.value) localStorage.setItem(USER_KEY, JSON.stringify(user.value))
    else localStorage.removeItem(USER_KEY)
  }

  function setSession(access: string, refresh: string, profile: UserProfile): void {
    accessToken.value = access
    refreshToken.value = refresh
    user.value = profile
    persist()
  }

  function clearSession(): void {
    accessToken.value = ''
    refreshToken.value = ''
    user.value = null
    persist()
  }

  async function login(username: string, password: string): Promise<void> {
    const tokens = await apiLogin(username, password)
    // 先持久化令牌，再拉取用户资料（getProfile 需要带令牌）
    accessToken.value = tokens.access_token
    refreshToken.value = tokens.refresh_token
    persist()
    const profile = await getProfile()
    setSession(tokens.access_token, tokens.refresh_token, profile)
    maybePromptGuestSync()
  }

  async function register(data: { username: string; email: string; password: string }): Promise<void> {
    const res = await apiRegister(data)
    setSession(res.access_token, res.refresh_token, res.user)
    maybePromptGuestSync()
  }

  function logout(): void {
    clearSession()
    router.push('/home')
  }

  /**
   * 游客拦截统一入口：已登录返回 true；未登录弹出登录提示弹窗并返回 false。
   */
  function requireAuth(redirect?: string): boolean {
    if (isLoggedIn.value) return true
    useUiStore().openLoginPrompt(redirect || router.currentRoute.value.fullPath)
    return false
  }

  /** 401 统一处理：清理登录态并弹出登录提示 */
  function handleUnauthorized(): void {
    clearSession()
    const ui = useUiStore()
    ui.openLoginPrompt(router.currentRoute.value.fullPath)
  }

  /** 游客数据存在时，登录/注册后弹同步提示 */
  function maybePromptGuestSync(): void {
    if (guestKeysExist()) {
      useUiStore().openSyncPrompt()
    }
  }

  return {
    accessToken,
    refreshToken,
    user,
    isLoggedIn,
    login,
    register,
    logout,
    requireAuth,
    handleUnauthorized,
  }
})
