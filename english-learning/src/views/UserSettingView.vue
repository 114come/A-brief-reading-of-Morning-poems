<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { updateProfile } from '@/api/english'
import { useAuthStore } from '@/stores/auth'
import { useSrsStore } from '@/stores/srs'
import { useUiStore } from '@/stores/ui'

const auth = useAuthStore()
const ui = useUiStore()
const srs = useSrsStore()

const nickname = ref(auth.user?.nickname || '')
const avatar = ref(auth.user?.avatar || '')
const saving = ref(false)

const avatarPreview = ref<string>(nickname.value ? nickname.value.slice(0, 1).toUpperCase() : 'U')

async function save(): Promise<void> {
  saving.value = true
  try {
    const profile = await updateProfile({
      nickname: nickname.value.trim() || undefined,
      avatar: avatar.value.trim() || undefined,
    })
    auth.user = profile
    avatarPreview.value = (profile.nickname || profile.username || 'U').slice(0, 1).toUpperCase()
    ui.showToast('设置已保存')
  } catch {
    ui.showToast('保存失败')
  } finally {
    saving.value = false
  }
}

async function resetAllData(): Promise<void> {
  if (!srs.bookId) {
    ui.showToast('尚未开始背单词')
    return
  }
  if (!window.confirm('确定清除全部学习数据吗？背诵记录、生词本和打卡都会被清空，无法恢复。')) return
  await srs.resetCurrentBook()
  ui.showToast('学习数据已清除')
}

onMounted(async () => {
  await srs.init()
})
</script>

<template>
  <div class="container">
    <div class="page-head">
      <div>
        <h1 class="page-title">账号设置</h1>
        <p class="page-desc">管理你的个人资料</p>
      </div>
    </div>

    <div class="setting-wrap">
      <div class="card card-pad setting-card">
        <div class="avatar-row">
          <span class="avatar-preview">
            <img v-if="auth.user?.avatar && auth.user.avatar.startsWith('http')" :src="auth.user.avatar" alt="avatar" />
            <span v-else>{{ avatarPreview }}</span>
          </span>
          <div>
            <div class="setting-name">{{ auth.user?.nickname || auth.user?.username }}</div>
            <div class="setting-account">@{{ auth.user?.username }}</div>
          </div>
        </div>

        <div class="form-item">
          <label class="field-label" for="set-nickname">昵称</label>
          <input id="set-nickname" v-model="nickname" class="input" type="text" placeholder="你的昵称" maxlength="50" />
        </div>

        <div class="form-item">
          <label class="field-label" for="set-avatar">头像</label>
          <input id="set-avatar" v-model="avatar" class="input" type="text" placeholder="头像图片链接（http 开头），或任意文本/Emoji" maxlength="255" />
        </div>

        <div class="form-item">
          <label class="field-label">邮箱</label>
          <input class="input" :value="auth.user?.email" type="text" disabled />
        </div>

        <div class="form-actions">
          <button class="btn btn-primary" type="button" :disabled="saving" @click="save">
            {{ saving ? '保存中…' : '保存设置' }}
          </button>
          <button class="btn btn-danger-soft" type="button" @click="auth.logout()">退出登录</button>
        </div>

        <div class="danger-zone">
          <div class="danger-title">数据管理</div>
          <p class="danger-tip">清除当前词库的背诵记录、生词本与打卡，回到全新状态。</p>
          <button class="btn btn-danger-soft btn-sm" type="button" @click="resetAllData">清除背单词学习数据</button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.setting-wrap {
  display: flex;
  justify-content: center;
}

.setting-card {
  width: 460px;
}

.avatar-row {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-bottom: 22px;
}

.avatar-preview {
  width: 56px;
  height: 56px;
  border-radius: 50%;
  background: var(--primary);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 22px;
  font-weight: 600;
  overflow: hidden;
  flex-shrink: 0;
}

.avatar-preview img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.setting-name {
  font-size: 16px;
  font-weight: 700;
}

.setting-account {
  font-size: 13px;
  color: var(--text-3);
}

.form-item {
  margin-bottom: 16px;
}

.form-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  margin-top: 20px;
}

.danger-zone {
  margin-top: 24px;
  padding-top: 18px;
  border-top: 1px solid var(--border);
}

.danger-title {
  font-size: 14px;
  font-weight: 700;
  color: var(--danger);
}

.danger-tip {
  font-size: 12px;
  color: var(--text-3);
  margin: 4px 0 12px;
}
</style>
