<script setup>
import { computed } from "vue";
import { session } from "../auth/session";
const home = computed(() =>
  session.user?.role === "admin" ? "/admin/dashboard" : "/member/dashboard",
);
</script>
<template>
  <section class="forbidden-page">
    <p class="forbidden-code">403</p>
    <h1>此页面仅限管理员访问</h1>
    <p>你的账号没有管理设置权限，如需调整请联系管理员。</p>
    <RouterLink :to="home" class="app-button button-primary"
      >返回数据看板</RouterLink
    >
  </section>
</template>
