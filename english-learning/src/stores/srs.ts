import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import { addWordbook, listBooks, listWords, saveSrsState } from '@/api/english'
import { useAuthStore } from '@/stores/auth'
import { useUiStore } from '@/stores/ui'
import { useOnboardingStore } from '@/stores/onboarding'
import {
  SUCCESSOR,
  addDaysStr,
  advancePhase,
  answerNew,
  answerReview,
  continueLearning as continueLearningEngine,
  currentWordId,
  ensureSession,
  hasUnlearned,
  isDayComplete,
  toRows,
  todayStr,
  type MemoryRow,
  type SessionState,
} from '@/composables/srsEngine'
import {
  clearGuestData,
  getAdapter,
  guestInitBook,
  loadGuestSettings,
  mergeGuestTags,
  saveGuestSettings,
} from '@/composables/srsStorage'
import type { CompleteResult, SrsSettings, SrsState, Word, WordBook } from '@/types'

const GUEST_CURRENT_BOOK_KEY = 'english_guest_current_book'
const STUDY_TAG_KEY = 'english_study_tag'

export const useSrsStore = defineStore('srs', () => {
  const auth = useAuthStore()
  const ui = useUiStore()
  const onboarding = useOnboardingStore()

  const books = ref<WordBook[]>([])
  const settings = ref<SrsSettings | null>(null)
  const memory = ref<MemoryRow[]>([])
  const session = ref<SessionState | null>(null)
  const bookId = ref<number | null>(null)
  const wordsByBook = ref<Map<number, Word[]>>(new Map())
  const initialized = ref(false)
  const loading = ref(false)

  const adapter = computed(() => getAdapter(auth.isLoggedIn))

  const currentBook = computed(() => books.value.find((b) => b.id === bookId.value) || null)
  const bookWords = computed<Word[]>(() => (bookId.value ? wordsByBook.value.get(bookId.value) || [] : []))
  const allWordIds = computed<number[]>(() => bookWords.value.map((w) => w.id))
  const dailyNewWords = computed(() => settings.value?.daily_new_words ?? 20)
  const onboarded = computed(() => Boolean(settings.value?.onboarding_done && settings.value.book_id === bookId.value))
  /** 当前学习分类（null=全部；core/common/advanced），持久化 localStorage */
  const selectedTag = ref<string | null>(localStorage.getItem(STUDY_TAG_KEY) || null)
  /** 按分类过滤后的可学单词池 */
  const studyWords = computed<Word[]>(() => {
    if (!selectedTag.value) return bookWords.value
    return bookWords.value.filter((w) => w.tag === selectedTag.value)
  })
  const studyWordIds = computed<number[]>(() => studyWords.value.map((w) => w.id))
  /** 词库中（当前分类内）是否还有未学单词（可继续学习） */
  const canContinue = computed(() => hasUnlearned(memory.value, studyWordIds.value))

  function setStudyTag(tag: string | null): void {
    selectedTag.value = tag
    if (tag) localStorage.setItem(STUDY_TAG_KEY, tag)
    else localStorage.removeItem(STUDY_TAG_KEY)
  }

  /** 引擎上下文（含当前记忆 Map + 会话副本） */
  function context() {
    return ensureSession(memory.value, session.value, dailyNewWords.value, studyWordIds.value)
  }

  function currentWord(): Word | null {
    const id = currentWordId(context())
    if (id == null) return null
    return bookWords.value.find((w) => w.id === id) || null
  }

  async function loadWords(bookIdValue: number): Promise<void> {
    // 完整加载本级词表（单本最多约 6000 词，一次拉全）
    let words = await listWords({ book_id: bookIdValue, limit: 20000 })
    // 游客：合并本地分类标签
    if (!auth.isLoggedIn) words = mergeGuestTags(bookIdValue, words)
    wordsByBook.value.set(bookIdValue, words)
  }

  let initPromise: Promise<void> | null = null

  function init(): Promise<void> {
    if (initialized.value) return Promise.resolve()
    if (!initPromise) initPromise = doInit().finally(() => (initPromise = null))
    return initPromise
  }

  async function doInit(): Promise<void> {
    loading.value = true
    try {
      books.value = await listBooks()
      let state: SrsState
      if (auth.isLoggedIn) {
        state = await adapter.value.loadState(0)
        settings.value = state.settings
        bookId.value = state.settings?.book_id ?? books.value[0]?.id ?? null
        memory.value = state.memory
        session.value = state.session
      } else {
        const gs = loadGuestSettings()
        settings.value = gs
        const savedBook = Number(localStorage.getItem(GUEST_CURRENT_BOOK_KEY) || 0) || gs?.book_id || books.value[0]?.id || null
        bookId.value = savedBook
        const localState = await adapter.value.loadState(savedBook || 0)
        memory.value = localState.memory
        session.value = localState.session
      }
      if (bookId.value) await loadWords(bookId.value)
      initialized.value = true
    } finally {
      loading.value = false
    }
  }

  /** 保存记忆+会话。只上传有学习状态的记忆行（status>=1），
   *  未学词（status=0）由 onboarding 批量初始化，避免大词书全量上传卡死。 */
  function persist(bookIdValue: number): Promise<void> {
    const dirty = memory.value.filter((m) => m.status >= 1 || m.wrong_count > 0)
    return adapter.value
      .saveState(bookIdValue, dirty, session.value)
      .catch(() => {
        /* 单次保存失败不阻塞 */
      })
  }

  /** 游客初始化某词书：本地写入全部 status=0 */
  function guestInit(bookIdValue: number, srsSettings: SrsSettings): void {
    const ids = wordsByBook.value.get(bookIdValue)?.map((w) => w.id) || []
    guestInitBook(bookIdValue, ids, { ...srsSettings, book_id: bookIdValue, onboarding_done: true })
    memory.value = ids.map((word_id) => ({ word_id, status: 0, next_review_date: null, interval: 0, wrong_count: 0 }))
    session.value = null
  }

  async function submitOnboarding(data: { target: string; book_id: number; daily_new_words: number; pronunciation: 'us' | 'uk'; autoplay: boolean }): Promise<void> {
    if (auth.isLoggedIn) {
      const { onboarding } = await import('@/api/english')
      settings.value = await onboarding(data)
      bookId.value = settings.value.book_id
      localStorage.removeItem(GUEST_CURRENT_BOOK_KEY)
      await loadWords(bookId.value)
      const state = await adapter.value.loadState(bookId.value)
      memory.value = state.memory
      session.value = state.session
    } else {
      const s: SrsSettings = {
        book_id: data.book_id,
        target: data.target,
        daily_new_words: data.daily_new_words,
        pronunciation: data.pronunciation,
        autoplay: data.autoplay,
        onboarding_done: true,
      }
      settings.value = s
      saveGuestSettings(s)
      localStorage.setItem(GUEST_CURRENT_BOOK_KEY, String(data.book_id))
      bookId.value = data.book_id
      await loadWords(data.book_id)
      guestInit(data.book_id, s)
    }
  }

  /** 开始/恢复当日学习（跨天时由引擎重建队列；等待词库加载完成避免空队列） */
  async function startDay(): Promise<void> {
    if (bookId.value && bookWords.value.length === 0) {
      await loadWords(bookId.value)
    }
    const ctx = ensureSession(memory.value, session.value, dailyNewWords.value, studyWordIds.value)
    memory.value = toRows(ctx)
    session.value = ctx.session
    await persist(bookId.value!)
  }

  /** 继续学习：完成一轮后从剩余未学池再取一批新词 */
  async function continueRound(): Promise<void> {
    if (!bookId.value) return
    const ctx = ensureSession(memory.value, session.value, dailyNewWords.value, studyWordIds.value)
    const next = continueLearningEngine(ctx, dailyNewWords.value, studyWordIds.value)
    memory.value = toRows(next)
    session.value = next.session
    completeResult.value = null
    await persist(bookId.value)
  }

  /** 学习中切换分类：以新分类池重建今日新词队列（仅未答题时调用） */
  async function rebuildNewBatch(): Promise<void> {
    if (!bookId.value) return
    // 传 null 会话强制按当前分类重建今日队列
    const ctx = ensureSession(memory.value, null, dailyNewWords.value, studyWordIds.value)
    memory.value = toRows(ctx)
    session.value = ctx.session
    completeResult.value = null
    await persist(bookId.value)
  }

  /** 作答：认识/不认识 */
  async function answer(known: boolean): Promise<void> {
    const ctx = ensureSession(memory.value, session.value, dailyNewWords.value, studyWordIds.value)
    const wordId = currentWordId(ctx)
    if (wordId == null) return
    let next: ReturnType<typeof answerReview>
    if (ctx.session.phase === 'review') next = answerReview(ctx, wordId, known)
    else next = answerNew(ctx, wordId, known)
    next = advancePhase(next, dailyNewWords.value, studyWordIds.value)

    memory.value = toRows(next)
    session.value = next.session

    if (!known) await autoAddWordbook(wordId)
    await persist(bookId.value!)

    if (isDayComplete(next)) await finishDay()
  }

  /** 给单词设置分类标签（登录云端/游客本地），并更新本地缓存 */
  async function setWordTag(wordId: number, tag: string | null): Promise<void> {
    if (!bookId.value) return
    if (auth.isLoggedIn) {
      const { setWordTag: apiSetTag } = await import('@/api/english')
      await apiSetTag(bookId.value, wordId, tag)
    } else {
      const { saveGuestTag } = await import('@/composables/srsStorage')
      saveGuestTag(bookId.value, wordId, tag)
    }
    // 更新本地 words 缓存
    const words = wordsByBook.value.get(bookId.value)
    if (words) {
      const target = words.find((w) => w.id === wordId)
      if (target) target.tag = tag
    }
  }

  async function autoAddWordbook(wordId: number): Promise<void> {
    if (!bookId.value) return
    if (auth.isLoggedIn) {
      try {
        await addWordbook(wordId, bookId.value)
      } catch {
        /* 已在生词本等场景忽略 */
      }
    } else {
      const { loadGuestWordbook, saveGuestWordbook } = await import('@/composables/srsStorage')
      const list = loadGuestWordbook(bookId.value)
      if (!list.includes(wordId)) saveGuestWordbook(bookId.value, [...list, wordId])
    }
  }

  /**
   * 测试答题对记忆状态的影响（不经过每日会话队列，直接改记忆行）：
   * - 答对：升级一次复习间隔（复用 SUCCESSOR 1→2→4→7→15）
   * - 答错：wrong_count+1、间隔重置1天；填空错题 next_review_date=today（次日置顶）
   */
  async function applyTestAnswer(wordId: number, known: boolean, isFill = false): Promise<void> {
    if (!bookId.value) return
    const memMap = new Map(memory.value.map((m) => [m.word_id, { ...m }]))
    let row = memMap.get(wordId)
    const today = todayStr()
    if (!row) {
      row = { word_id: wordId, status: 1, next_review_date: today, interval: 1, wrong_count: 0 }
    }
    if (known) {
      row.wrong_count = 0
      if (row.status === 1) {
        row.interval = SUCCESSOR[row.interval] ?? 1
        row.next_review_date = addDaysStr(today, row.interval)
      }
    } else {
      row.wrong_count += 1
      row.interval = 1
      row.status = 1
      row.next_review_date = isFill ? today : addDaysStr(today, 1)
    }
    memMap.set(wordId, row)
    memory.value = [...memMap.values()]
    if (!known) await autoAddWordbook(wordId)
    // 增量保存：只上传变化的这一行，避免全量 7500 行请求超时
    await saveSrsState({ book_id: bookId.value, memory: [row], session: null })
  }

  const completeResult = ref<CompleteResult | null>(null)

  async function finishDay(): Promise<void> {
    if (!bookId.value) return
    const counts = {
      review_count: session.value?.review_done ?? 0,
      new_count: session.value?.new_done ?? 0,
      wrong_count: session.value?.wrong_total ?? 0,
    }
    const result = await adapter.value.completeDay({
      book_id: bookId.value,
      study_date: todayStr(),
      ...counts,
    })
    completeResult.value = result
    if (!auth.isLoggedIn) {
      // 游客：本地打卡已写，完成后提示登录同步
      ui.showToast('今日学习完成！登录可同步并保存打卡')
    }
  }

  /** 切换词书：有历史则恢复，无历史则打开引导初始化 */
  async function switchBook(targetBookId: number): Promise<void> {
    const state = await adapter.value.loadState(targetBookId)
    if (auth.isLoggedIn) {
      if (state.memory.length > 0) {
        bookId.value = targetBookId
        memory.value = state.memory
        session.value = state.session
        settings.value = state.settings ?? settings.value
        if (settings.value) settings.value = { ...settings.value, book_id: targetBookId }
        localStorage.setItem(GUEST_CURRENT_BOOK_KEY, '')
        await loadWords(targetBookId)
        return
      }
    } else {
      const gs = loadGuestSettings()
      if (gs && gs.book_id === targetBookId) {
        bookId.value = targetBookId
        memory.value = state.memory
        session.value = state.session
        await loadWords(targetBookId)
        return
      }
    }
    // 未初始化 → 打开引导
    onboarding.open(targetBookId)
  }

  async function resetCurrentBook(): Promise<void> {
    if (!bookId.value) return
    await adapter.value.reset(bookId.value)
    settings.value = null
    memory.value = []
    session.value = null
  }

  async function syncToCloud(): Promise<void> {
    if (!auth.isLoggedIn) return
    const { clearGuestData, loadGuestSettings, loadGuestWordbook, GUEST_MEMORY_KEY } = await import('@/composables/srsStorage')
    const gs = loadGuestSettings()
    const guestBookId = gs?.book_id
    if (!guestBookId) {
      clearGuestData()
      return
    }
    // 直接从 localStorage 读取游客数据（而非 store 里尚未加载的云端状态）
    let guestMemory: MemoryRow[] = []
    try {
      const raw = localStorage.getItem(GUEST_MEMORY_KEY(guestBookId))
      if (raw) guestMemory = JSON.parse(raw) as MemoryRow[]
    } catch {
      /* ignore */
    }
    const wordbook = loadGuestWordbook(guestBookId)
    await adapter.value.syncGuest(guestBookId, guestMemory, wordbook)
    // 同步后把用户设置指向游客词库并加载，使其无缝继续
    if (gs) {
      const { onboarding: apiOnboarding } = await import('@/api/english')
      settings.value = await apiOnboarding({
        target: gs.target,
        book_id: guestBookId,
        daily_new_words: gs.daily_new_words,
        pronunciation: gs.pronunciation,
        autoplay: gs.autoplay,
      })
    }
    bookId.value = guestBookId
    await loadWords(guestBookId)
    const state = await adapter.value.loadState(guestBookId)
    memory.value = state.memory
    session.value = state.session
    clearGuestData()
    ui.showToast('本地学习数据已同步到云端')
  }

  function setSettings(patch: Partial<SrsSettings>): void {
    if (!settings.value) return
    settings.value = { ...settings.value, ...patch }
    if (auth.isLoggedIn) {
      void import('@/api/english').then((m) => m.onboarding({
        target: settings.value!.target,
        book_id: settings.value!.book_id,
        daily_new_words: settings.value!.daily_new_words,
        pronunciation: settings.value!.pronunciation,
        autoplay: settings.value!.autoplay,
      }))
    } else {
      saveGuestSettings(settings.value)
    }
  }

  return {
    books,
    settings,
    memory,
    session,
    bookId,
    bookWords,
    currentBook,
    allWordIds,
    studyWords,
    studyWordIds,
    selectedTag,
    dailyNewWords,
    onboarded,
    canContinue,
    completeResult,
    loading,
    initialized,
    currentWord,
    init,
    startDay,
    continueRound,
    rebuildNewBatch,
    answer,
    finishDay,
    submitOnboarding,
    switchBook,
    resetCurrentBook,
    syncToCloud,
    setSettings,
    setStudyTag,
    setWordTag,
    applyTestAnswer,
  }
})
