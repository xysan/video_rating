<script setup>
import { onMounted, ref } from 'vue'
import { getHealth } from './api/health'

const status = ref('检查中…')
onMounted(async () => {
  try {
    status.value = await getHealth()
  } catch (error) {
    status.value = `连接失败：${error.message}`
  }
})
</script>

<template>
  <main>
    <h1>项目初始化成功</h1>
    <p role="status" aria-live="polite">后端状态：{{ status }}</p>
  </main>
</template>
