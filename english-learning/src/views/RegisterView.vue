<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { ApiError } from '@/api/http'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
const router = useRouter()

const username = ref('')
const email = ref('')
const password = ref('')
const confirm = ref('')
const error = ref('')
const submitting = ref(false)

const emailRe = /^[^\s@]+@[^\s@]+\.[^\s@]+$/

function validate(): string {
  if (username.value.trim().length < 2) return '用户名至少 2 个字符'
  if (!emailRe.test(email.value.trim())) return '请输入正确的邮箱'
  if (password.value.length < 6) return '密码至少 6 位'
  if (password.value !== confirm.value) return '两次输入的密码不一致'
  return ''
}

async function submit(): Promise<void> {
  error.value = validate()
  if (error.value) return
  submitting.value = true
  try {
    await auth.register({
      username: username.value.trim(),
      email: email.value.trim(),
      password: password.value,
    })
    router.push('/home')
  } catch (e) {
    error.value = e instanceof ApiError ? e.message : '注册失败，请稍后再试'
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
          <h1 class="auth-title">注册账号</h1>
          <p class="auth-sub">免费注册，立即开始学习</p>
        </div>

        <form @submit.prevent="submit">
          <div class="form-item">
            <label class="field-label" for="reg-username">用户名</label>
            <input id="reg-username" v-model="username" class="input" type="text" placeholder="2-50 个字符" autocomplete="username" />
          </div>
          <div class="form-item">
            <label class="field-label" for="reg-email">邮箱</label>
            <input id="reg-email" v-model="email" class="input" type="email" placeholder="you@example.com" autocomplete="email" />
          </div>
          <div class="form-item">
            <label class="field-label" for="reg-password">密码</label>
            <input id="reg-password" v-model="password" class="input" type="password" placeholder="至少 6 位" autocomplete="new-password" />
          </div>
          <div class="form-item">
            <label class="field-label" for="reg-confirm">确认密码</label>
            <input id="reg-confirm" v-model="confirm" class="input" type="password" placeholder="再次输入密码" autocomplete="new-password" />
          </div>

          <p v-if="error" class="auth-error">{{ error }}</p>

          <button class="btn btn-primary auth-submit" type="submit" :disabled="submitting">
            {{ submitting ? '注册中…' : '注册' }}
          </button>
        </form>

        <p class="auth-switch">
          已有账号？
          <RouterLink to="/login" class="auth-link">直接登录</RouterLink>
        </p>
      </div>
    </div>
  </div>
</template>

<style scoped>
.auth-wrap {
  display: flex;
  justify-content: center;
  padding-top: 40px;
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
  margin-bottom: 14px;
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
