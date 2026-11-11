import { createRouter, createWebHistory } from "vue-router";
import { session, clearSession } from "../auth/session";
import { loadUser, onUnauthorized } from "../api/client";
import LoginView from "../views/LoginView.vue";

import AppLayout from "../components/ui/AppLayout.vue";
const pages = [
  ["member/dashboard", "数据看板", "OVERVIEW"],
  ["member/scores", "视频得分", "VIDEO SCORES"],
  ["admin/dashboard", "数据看板", "OVERVIEW"],
  ["admin/scores", "视频得分", "VIDEO SCORES"],
  ["admin/settings", "管理设置", "SETTINGS"],
];
export const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: "/login", component: LoginView },
    {
      path: "/",
      component: AppLayout,
      children: [
        {
          path: "forbidden",
          component: () => import("../views/ForbiddenView.vue"),
          meta: { title: "访问受限" },
        },
        ...pages.map(([path, title, english]) => ({
          path,
          component: path.endsWith("/dashboard")
            ? () => import("../views/DashboardView.vue")
            : path.endsWith("/scores")
              ? () => import("../views/ScoresView.vue")
              : () => import("../views/SettingsView.vue"),
          meta: { title, english, admin: path.startsWith("admin/") },
        })),
      ],
    },
    { path: "/admin", redirect: "/admin/dashboard" },
    { path: "/member", redirect: "/member/dashboard" },
    { path: "/:pathMatch(.*)*", redirect: "/" },
  ],
});
router.beforeEach(async (to) => {
  if (!session.token) return to.path === "/login" ? true : "/login";
  try {
    if (!session.user) await loadUser();
  } catch {
    clearSession();
    return to.path === "/login" ? true : "/login";
  }
  const home =
    session.user.role === "admin" ? "/admin/dashboard" : "/member/dashboard";
  if (to.path === "/login" || to.path === "/") return home;
  if (to.meta.admin && session.user.role !== "admin")
    return to.path === "/admin/settings" ? "/forbidden" : "/member/dashboard";
});
onUnauthorized(() => {
  if (router.currentRoute.value.path !== "/login") router.replace("/login");
});
