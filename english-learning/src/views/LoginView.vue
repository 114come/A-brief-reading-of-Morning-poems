<script setup lang="ts">
import { ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ApiError } from '@/api/http'
import { useAuthStore } from '@/stores/auth'
import { useUiStore } from '@/stores/ui'

const auth = useAuthStore()
const ui = useUiStore()
const route = useRoute()
const router = useRouter()

const username = ref('')
const password = ref('')
const error = ref('')
const submitting = ref(false)

async function submit(): Promise<void> {
  error.value = ''
  if (!username.value.trim() || !password.value) {
    error.value = '请输入用户名和密码'
    return
  }
  submitting.value = true
  try {
    await auth.login(username.value.trim(), password.value)
    // 登录后回到用户原本想去的页面
    const redirect = (route.query.redirect as string) || ui.loginRedirect || '/home'
    ui.loginRedirect = '/home'
    router.push(redirect)
  } catch (e) {
    error.value = e instanceof ApiError ? e.message : '登录失败，请稍后再试'
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <div class="container">
    <div class="auth-wrap">
      <div class="card card-pad auth-card">
        <div class="auth-head">
          <div class="auth-logo">En</div>
          <h1 class="auth-title">登录朝词浅阅</h1>
          <p class="auth-sub">继续你的英语学习旅程</p>
        </div>

        <form @submit.prevent="submit">
          <div class="form-item">
            <label class="field-label" for="login-username">用户名</label>
            <input id="login-username" v-model="username" class="input" type="text" placeholder="请输入用户名" autocomplete="username" />
          </div>
          <div class="form-item">
            <label class="field-label" for="login-password">密码</label>
            <input id="login-password" v-model="password" class="input" type="password" placeholder="请输入密码" autocomplete="current-password" />
          </div>

          <p v-if="error" class="auth-error">{{ error }}</p>

          <button class="btn btn-primary auth-submit" type="submit" :disabled="submitting">
            {{ submitting ? '登录中…' : '登录' }}
          </button>
        </form>

        <p class="auth-switch">
          还没有账号？
          <RouterLink to="/register" class="auth-link">立即注册</RouterLink>
        </p>
      </div>
    </div>
  </div>
</template>

<style scoped>
.auth-wrap {
  display: flex;
  justify-content: center;
  padding-top: 48px;
}

.auth-card {
  width: 400px;
  padding: 32px;
}

.auth-head {
  text-align: center;
  margin-bottom: 24px;
}

.auth-logo {
  width: 48px;
  height: 48px;
  margin: 0 auto 12px;
  border-radius: 14px;
  background: var(--brand-gradient);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 20px;
  font-weight: 600;
}

.auth-title {
  font-size: 20px;
  font-weight: 700;
}

.auth-sub {
  margin-top: 4px;
  font-size: 13px;
  color: var(--text-2);
}

.form-item {
  margin-bottom: 16px;
}

.auth-error {
  margin-bottom: 14px;
  font-size: 13px;
  color: var(--danger);
  background: var(--danger-soft);
  padding: 8px 12px;
  border-radius: 8px;
}

.auth-submit {
  width: 100%;
  height: 42px;
  margin-top: 4px;
}

.auth-switch {
  margin-top: 18px;
  text-align: center;
  font-size: 13px;
  color: var(--text-2);
}

.auth-link {
  color: var(--primary);
  font-weight: 600;
}
</style>
