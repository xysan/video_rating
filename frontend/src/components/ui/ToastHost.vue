<script setup>
import { notices, dismiss, toastTarget } from "./toast";
</script>
<template>
  <Teleport :to="toastTarget || 'body'">
    <div class="toast-stack" aria-live="polite" aria-atomic="false">
      <div
        v-for="item in notices"
        :key="item.id"
        class="toast-item"
        :class="`toast-${item.type}`"
        :role="item.type === 'error' ? 'alert' : 'status'"
      >
        <span>{{ item.type === "error" ? "!" : "✓" }}</span>
        <p>{{ item.message }}</p>
        <button aria-label="关闭提示" @click="dismiss(item.id)">×</button>
      </div>
    </div>
  </Teleport>
</template>
