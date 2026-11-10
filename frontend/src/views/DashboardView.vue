<script setup>
import { computed, ref, onMounted, onBeforeUnmount } from "vue";
import {
  PhArrowClockwise,
  PhArrowLeft,
  PhArrowRight,
  PhPause,
  PhPlay,
  PhTrophy,
} from "@phosphor-icons/vue";
import { api } from "../api/client";
import GlassPanel from "../components/ui/GlassPanel.vue";
import AppButton from "../components/ui/AppButton.vue";
import VideoCard from "../components/dashboard/VideoCard.vue";
import VideoCover from "../components/dashboard/VideoCover.vue";
import { scoreOf, titleOf, nextScroll } from "../utils/dashboard";
import "../styles/dashboard.css";
const data = ref({ top_videos: [], videos: [] });
const loading = ref(true),
  refreshing = ref(false),
  error = ref(""),
  updated = ref(null);
const now = ref(new Date()),
  rail = ref(null),
  paused = ref(false),
  interacting = ref(false),
  reduced = ref(false);
const dateText = computed(() =>
  new Intl.DateTimeFormat("zh-CN", {
    month: "long",
    day: "numeric",
    weekday: "long",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  }).format(now.value),
);
const top = computed(() => data.value.top_videos.slice(0, 5));
const videos = computed(() =>
  [...data.value.videos].sort(
    (a, b) =>
      (b.publish_date || "").localeCompare(a.publish_date || "") ||
      (b.id || 0) - (a.id || 0),
  ),
);
let controller, clockTimer, refreshTimer, slideTimer, motion;
async function refresh() {
  if (refreshing.value) return;
  refreshing.value = true;
  controller = new AbortController();
  try {
    const result = await api.get("/api/member/dashboard", {
      signal: controller.signal,
    });
    if (
      !Array.isArray(result.data.top_videos) ||
      !Array.isArray(result.data.videos)
    )
      throw new Error("看板响应格式异常");
    data.value = result.data;
    updated.value = new Date();
    error.value = "";
  } catch (err) {
    if (err.code !== "ERR_CANCELED")
      error.value = updated.value
        ? "刷新失败，正在显示上次成功获取的数据"
        : "暂时无法加载看板，请重试";
  } finally {
    loading.value = false;
    refreshing.value = false;
  }
}
function move(direction) {
  const el = rail.value;
  if (!el) return;
  el.scrollTo({
    left: nextScroll(el.scrollLeft, el.scrollWidth, el.clientWidth, direction),
    behavior: reduced.value ? "instant" : "smooth",
  });
}
function motionChanged(event) {
  reduced.value = event.matches;
}
function focusOut(event) {
  if (!event.currentTarget.contains(event.relatedTarget))
    interacting.value = false;
}
onMounted(() => {
  motion = window.matchMedia("(prefers-reduced-motion: reduce)");
  reduced.value = motion.matches;
  motion.addEventListener("change", motionChanged);
  refresh();
  clockTimer = setInterval(() => {
    now.value = new Date();
  }, 1000);
  refreshTimer = setInterval(() => {
    if (!document.hidden) refresh();
  }, 60000);
  slideTimer = setInterval(() => {
    if (
      !paused.value &&
      !interacting.value &&
      !reduced.value &&
      !document.hidden
    )
      move(1);
  }, 7000);
});
onBeforeUnmount(() => {
  controller?.abort();
  [clockTimer, refreshTimer, slideTimer].forEach(clearInterval);
  motion?.removeEventListener("change", motionChanged);
});
</script>
<template>
  <section class="dashboard" :aria-busy="loading">
    <header class="dashboard-heading">
      <div>
        <p class="eyebrow">THE CREATIVE PULSE</p>
        <h1>数据看板<span>每一份创作，都值得被看见。</span></h1>
      </div>
      <div class="dashboard-tools">
        <time :datetime="now.toISOString()">{{ dateText }}</time
        ><AppButton
          variant="secondary"
          :loading="refreshing"
          class="dashboard-refresh"
          aria-label="刷新看板"
          @click="refresh"
          ><PhArrowClockwise v-if="!refreshing" />刷新</AppButton
        >
      </div>
    </header>
    <p v-if="error" class="dashboard-notice" role="alert">
      {{ error
      }}<button @click="refresh" :disabled="refreshing">重新加载</button>
    </p>
    <div class="dashboard-zones">
      <GlassPanel class="leaderboard" aria-labelledby="ranking-title">
        <header class="section-heading">
          <div>
            <span class="section-kicker">THE TOP FIVE</span>
            <h2 id="ranking-title"><PhTrophy aria-hidden="true" />高光作品</h2>
          </div>
          <span class="section-note">近 30 天 · 综合得分排名</span>
        </header>
        <div v-if="loading" class="ranking-grid" aria-label="排行榜加载中">
          <div v-for="n in 5" :key="n" class="rank-skeleton skeleton" />
        </div>
        <TransitionGroup
          v-else-if="top.length"
          name="rank"
          :style="{ '--rank-columns': top.length }"
          tag="ol"
          class="ranking-grid"
        >
          <li
            v-for="(video, index) in top"
            :key="`${video.up_name}-${video.video_title || video.title}`"
            class="rank-card"
            :class="`rank-${index + 1}`"
          >
            <VideoCover :src="video.cover_url" :alt="titleOf(video)"
              ><span class="rank-number">{{
                String(index + 1).padStart(2, "0")
              }}</span></VideoCover
            >
            <div class="rank-info">
              <h3 :title="titleOf(video)">{{ titleOf(video) }}</h3>
              <div>
                <span :title="video.up_name">{{ video.up_name }}</span
                ><strong
                  >{{ scoreOf(video)?.toFixed(2) ?? "—"
                  }}<small>分</small></strong
                >
              </div>
            </div>
          </li>
        </TransitionGroup>
        <div v-else class="dashboard-empty">
          <PhTrophy aria-hidden="true" />
          <p>{{ error ? "排行榜暂不可用" : "高光时刻，正在酝酿" }}</p>
          <span>{{
            error ? "请重试获取真实数据" : "近 30 天暂无已评分作品"
          }}</span>
        </div>
      </GlassPanel>
      <section class="video-section" aria-labelledby="video-title">
        <header class="section-heading">
          <div>
            <span class="section-kicker">LATEST RELEASES</span>
            <h2 id="video-title">
              创作轨迹
              <span class="video-total"
                >{{ loading ? "—" : videos.length }} 部</span
              >
            </h2>
          </div>
          <div class="rail-controls">
            <span class="section-note">最新发布在前 · 横向浏览</span
            ><button
              class="rail-button"
              :disabled="videos.length < 2 || reduced"
              :aria-label="paused || reduced ? '开启自动轮播' : '暂停自动轮播'"
              :aria-pressed="!paused && !reduced"
              @click="paused = !paused"
            >
              <PhPlay v-if="paused || reduced" /><PhPause v-else /></button
            ><button
              class="rail-button"
              aria-label="上一组视频"
              :disabled="!videos.length"
              @click="move(-1)"
            >
              <PhArrowLeft /></button
            ><button
              class="rail-button"
              aria-label="下一组视频"
              :disabled="!videos.length"
              @click="move(1)"
            >
              <PhArrowRight />
            </button>
          </div>
        </header>
        <div v-if="loading" class="video-rail" aria-label="视频加载中">
          <div v-for="n in 5" :key="n" class="video-skeleton skeleton" />
        </div>
        <div
          v-else-if="videos.length"
          ref="rail"
          class="video-rail"
          tabindex="0"
          role="region"
          aria-label="近30天视频，使用左右方向键浏览"
          @mouseenter="interacting = true"
          @mouseleave="interacting = false"
          @focusin="interacting = true"
          @focusout="focusOut"
          @touchstart.passive="paused = true"
          @wheel.passive="paused = true"
          @keydown.left.prevent="move(-1)"
          @keydown.right.prevent="move(1)"
        >
          <VideoCard
            v-for="video in videos"
            :key="
              video.id ?? video.bv_id ?? `${video.up_name}-${video.video_title}`
            "
            :video="video"
          />
        </div>
        <div v-else class="dashboard-empty videos-empty">
          <p>{{ error ? "视频暂不可用" : "近 30 天暂无发布记录" }}</p>
          <span>同步到真实视频后，将在这里展示</span>
        </div>
      </section>
    </div>
    <footer class="dashboard-footnote">
      <span>近 30 天发布 · 发布满 15 天后计算得分</span
      ><span
        >{{
          updated
            ? `最近更新 ${updated.toLocaleTimeString("zh-CN", { hour12: false })}`
            : "等待数据"
        }}
        · 每分钟刷新</span
      >
    </footer>
  </section>
</template>
