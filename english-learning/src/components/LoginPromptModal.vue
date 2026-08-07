<script setup lang="ts">
import { useUiStore } from '@/stores/ui'

const ui = useUiStore()
</script>

<template>
  <Teleport to="body">
    <transition name="modal">
      <div v-if="ui.loginPromptOpen" class="modal-mask" @click.self="ui.closeLoginPrompt()">
        <div class="modal-box">
          <div class="modal-title">需要登录</div>
          <p class="modal-desc">
            登录后可同步你的生词本、收藏、阅读笔记与打卡数据，随时随地继续学习。
          </p>
          <div class="modal-actions">
            <button class="btn btn-ghost" type="button" @click="ui.closeLoginPrompt()">取消</button>
            <button class="btn btn-primary" type="button" @click="ui.goLogin()">前往登录</button>
          </div>
        </div>
      </div>
    </transition>
  </Teleport>
</template>

<style scoped>
.modal-enter-active,
.modal-leave-active {
  transition: opacity 0.2s ease;
}

.modal-enter-from,
.modal-leave-to {
  opacity: 0;
}
</style>
