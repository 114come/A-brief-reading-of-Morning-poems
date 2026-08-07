import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

declare module 'vue-router' {
  interface RouteMeta {
    /** 需要登录；游客访问时弹出登录提示弹窗（不跳转） */
    requiresLogin?: boolean
    /** 顶部主导航高亮对应的 key */
    navKey?: string
  }
}

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    { path: '/', redirect: '/home' },
    {
      path: '/home',
      name: 'Home',
      component: () => import('@/views/HomeView.vue'),
      meta: { navKey: 'home' },
    },
    {
      path: '/word',
      name: 'Word',
      component: () => import('@/views/WordView.vue'),
      meta: { navKey: 'word' },
    },
    {
      path: '/word/notebook',
      name: 'WordNotebook',
      component: () => import('@/views/WordNotebookView.vue'),
      meta: { requiresLogin: true },
    },
    {
      path: '/reading',
      name: 'Reading',
      component: () => import('@/views/ReadingView.vue'),
      meta: { navKey: 'reading', requiresLogin: true },
    },
    {
      path: '/reading/note',
      name: 'ReadingNote',
      component: () => import('@/views/ReadingNoteView.vue'),
      meta: { requiresLogin: true },
    },
    {
      path: '/study-center',
      name: 'StudyCenter',
      component: () => import('@/views/StudyCenterView.vue'),
      meta: { navKey: 'study-center' },
    },
    {
      path: '/study-center/checkin',
      name: 'Checkin',
      component: () => import('@/views/CheckinView.vue'),
      meta: { requiresLogin: true },
    },
    {
      path: '/collect',
      name: 'Collect',
      component: () => import('@/views/CollectView.vue'),
      meta: { requiresLogin: true },
    },
    {
      path: '/login',
      name: 'Login',
      component: () => import('@/views/LoginView.vue'),
    },
    {
      path: '/register',
      name: 'Register',
      component: () => import('@/views/RegisterView.vue'),
    },
    {
      path: '/user/setting',
      name: 'UserSetting',
      component: () => import('@/views/UserSettingView.vue'),
      meta: { requiresLogin: true },
    },
    { path: '/:pathMatch(.*)*', redirect: '/home' },
  ],
})

// 游客访问私有页面：弹出登录提示弹窗并取消导航（不跳转，无死循环）
router.beforeEach((to) => {
  if (to.meta.requiresLogin) {
    const auth = useAuthStore()
    if (!auth.isLoggedIn) {
      auth.requireAuth()
      return false
    }
  }
  return true
})

export default router
