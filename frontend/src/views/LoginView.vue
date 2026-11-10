<script setup>
import { ref } from "vue";
import { useRouter } from "vue-router";
import {
  PhUser,
  PhLockKey,
  PhArrowRight,
  PhShieldCheck,
  PhWarningCircle,
} from "@phosphor-icons/vue";
import GlassPanel from "../components/ui/GlassPanel.vue";
import AppInput from "../components/ui/AppInput.vue";
import AppButton from "../components/ui/AppButton.vue";
import { api, loadUser } from "../api/client";
import { setToken, clearSession } from "../auth/session";
const username = ref(""),
  password = ref(""),
  loading = ref(false),
  error = ref("");
const router = useRouter();
async function login() {
  if (loading.value) return;
  error.value = "";
  loading.value = true;
  try {
    const { data } = await api.post("/api/auth/login", {
      username: username.value.trim(),
      password: password.value,
    });
    if (!data.access_token) throw new Error("登录响应无效");
    setToken(data.access_token);
    const user = await loadUser();
    password.value = "";
    await router.replace(
      user.role === "admin" ? "/admin/dashboard" : "/member/dashboard",
    );
  } catch (err) {
    clearSession();
    error.value =
      err.response?.status === 401
        ? "用户名或密码错误"
        : "暂时无法登录，请检查网络或稍后重试";
  } finally {
    loading.value = false;
  }
}
</script>
<template>
  <main class="login-page">
    <header class="login-topbar">
      <div class="brand-lockup">
        <span class="brand-icon"><img src="/brand/mark.png" alt="" /></span
        ><strong>NESTLEHOUSE</strong>
      </div>
      <span class="topbar-note"
        >CREATOR WORKSPACE <span class="tiny-dot"
      /></span>
    </header>
    <div class="login-center">
      <GlassPanel class="login-panel"
        ><section class="brand-story" aria-label="品牌介绍">
          <div class="eyebrow"><span class="tiny-dot" /> THE CREATIVE NEST</div>
          <h1>Good ideas.<br /><span>Great impact.</span></h1>
          <p>让每一份创作，<br />都被认真看见。</p>
          <div class="mascot-stage">
            <img src="/brand/mark.png" alt="NESTLEHOUSE 企鹅标识" /><span
              class="mascot-caption"
              >MADE OF IDEAS.</span
            >
          </div>
          <div class="story-bottom">
            <span>NESTLEHOUSE STUDIO</span><span>01 / CREATE</span>
          </div>
        </section>
        <section class="login-form-area">
          <div class="form-kicker">YOUR WORKSPACE, REIMAGINED</div>
          <h2>欢迎回巢</h2>
          <p class="form-description">登录你的账号，开启今天的创作旅程。</p>
          <form @submit.prevent="login">
            <AppInput
              id="username"
              v-model="username"
              label="账号"
              placeholder="请输入账号"
              autocomplete="username"
              required
              :disabled="loading"
              :error="!!error"
              :aria-describedby="error ? 'login-error' : undefined"
              ><template #icon><PhUser /></template></AppInput
            ><AppInput
              id="password"
              v-model="password"
              label="密码"
              type="password"
              placeholder="请输入密码"
              autocomplete="current-password"
              required
              :disabled="loading"
              :error="!!error"
              :aria-describedby="error ? 'login-error' : undefined"
              ><template #icon><PhLockKey /></template
            ></AppInput>
            <div class="form-status" aria-live="polite">
              <p v-if="error" id="login-error" class="error-message">
                <PhWarningCircle />{{ error }}
              </p>
            </div>
            <AppButton type="submit" :loading="loading" class="login-submit"
              >{{ loading ? "正在登录" : "登录工作台"
              }}<PhArrowRight v-if="!loading"
            /></AppButton>
          </form>
          <div class="access-note">
            <PhShieldCheck /><span
              >仅限团队成员访问 · 如需账号，请联系管理员</span
            >
          </div>
        </section></GlassPanel
      >
      <p class="login-footer">
        灵感在这里发生，成长在这里被看见。<span
          >NESTLEHOUSE © {{ new Date().getFullYear() }}</span
        >
      </p>
    </div>
  </main>
</template>
