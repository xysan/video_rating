<script setup>
import { computed } from "vue";
import { useRouter, useRoute } from "vue-router";
import {
  PhSquaresFour,
  PhChartBar,
  PhSlidersHorizontal,
  PhSignOut,
  PhArrowUpRight,
} from "@phosphor-icons/vue";
import { session, clearSession } from "../../auth/session";
import GlassPanel from "./GlassPanel.vue";
const router = useRouter(),
  route = useRoute();
const prefix = computed(() =>
  session.user?.role === "admin" ? "/admin" : "/member",
);
const nav = computed(() => [
  { path: `${prefix.value}/dashboard`, title: "数据看板", icon: PhSquaresFour },
  { path: `${prefix.value}/scores`, title: "视频得分", icon: PhChartBar },
  ...(session.user?.role === "admin"
    ? [
        {
          path: "/admin/settings",
          title: "管理设置",
          icon: PhSlidersHorizontal,
        },
      ]
    : []),
]);
function logout() {
  clearSession();
  router.replace("/login");
}
</script>
<template>
  <div class="app-layout">
    <GlassPanel as="aside" class="sidebar"
      ><RouterLink
        :to="`${prefix}/dashboard`"
        class="brand-lockup"
        aria-label="返回数据看板"
        ><span class="brand-icon"><img src="/brand/mark.png" alt="" /></span
        ><span
          ><strong>NESTLEHOUSE</strong><small>创作表现工作台</small></span
        ></RouterLink
      >
      <div class="nav-caption">WORKSPACE</div>
      <nav aria-label="主要导航">
        <RouterLink
          v-for="item in nav"
          :key="item.path"
          :to="item.path"
          :aria-label="item.title"
          class="nav-item"
          :aria-current="route.path === item.path ? 'page' : undefined"
          ><component :is="item.icon" weight="duotone" /><span>{{
            item.title
          }}</span
          ><PhArrowUpRight class="nav-arrow"
        /></RouterLink>
      </nav>
      <div class="sidebar-bottom">
        <div class="user-summary">
          <span class="avatar">{{
            (session.user?.display_name || "U").slice(0, 1)
          }}</span
          ><span
            ><strong>{{ session.user?.display_name }}</strong
            ><small>{{
              session.user?.role === "admin" ? "管理员" : "普通成员"
            }}</small></span
          >
        </div>
        <button class="logout" aria-label="退出登录" @click="logout">
          <PhSignOut /><span>退出登录</span>
        </button>
      </div></GlassPanel
    >
    <main
      class="workspace-content"
      :class="{ 'dashboard-workspace': route.path.endsWith('/dashboard') }"
    >
      <header class="workspace-header">
        <span
          >工作空间 <span class="breadcrumb-separator">/</span>
          {{ route.meta.title }}</span
        ><span class="workspace-badge">NESTLEHOUSE · TEAM</span>
      </header>
      <RouterView />
    </main>
  </div>
</template>
