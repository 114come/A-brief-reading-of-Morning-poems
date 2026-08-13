<script setup lang="ts">
defineProps<{ quote: string; source: string }>()
</script>

<template>
  <div class="daily-quote">
    <span class="dq-mark">「</span>
    <p class="dq-text">{{ quote }}</p>
    <span class="dq-source">—— {{ source }}</span>
  </div>
</template>

<style scoped>
.daily-quote {
  display: flex;
  align-items: baseline;
  gap: 8px;
  padding: 14px 20px;
  border-radius: var(--radius-lg);
  background: linear-gradient(120deg, var(--sun-soft), var(--primary-soft));
  color: var(--text-2);
  font-size: var(--fs-base);
}
.dq-mark {
  color: var(--sun);
  font-size: 18px;
  line-height: 1;
}
.dq-text {
  flex: 1;
  font-family: var(--font-display);
}
.dq-source {
  font-size: var(--fs-xs);
  color: var(--text-3);
  white-space: nowrap;
}
</style>
