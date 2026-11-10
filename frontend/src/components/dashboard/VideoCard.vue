<script setup>
import { computed } from "vue";
import {
  PhPlay,
  PhHeart,
  PhCoins,
  PhStar,
  PhChatCircle,
  PhShareNetwork,
  PhChats,
  PhSparkle,
} from "@phosphor-icons/vue";
import GlassPanel from "../ui/GlassPanel.vue";
import VideoCover from "./VideoCover.vue";
import {
  scoreOf,
  isHighScore,
  formatCount,
  titleOf,
} from "../../utils/dashboard";
const props = defineProps({ video: { type: Object, required: true } });
const score = computed(() => scoreOf(props.video));
const metrics = [
  ["play_count", "播放", PhPlay],
  ["like_count", "点赞", PhHeart],
  ["coin_count", "投币", PhCoins],
  ["favorite_count", "收藏", PhStar],
  ["comment_count", "评论", PhChatCircle],
  ["share_count", "分享", PhShareNetwork],
  ["danmaku_count", "弹幕", PhChats],
];
</script>
<template>
  <GlassPanel
    as="article"
    :blur="false"
    class="video-card"
    :class="{ 'video-card-high': isHighScore(video) }"
    :aria-label="titleOf(video)"
  >
    <VideoCover :src="video.cover_url" :alt="titleOf(video)"
      ><time class="publish-badge" :datetime="video.publish_date">{{
        video.publish_date?.slice(0, 10) || "日期未知"
      }}</time></VideoCover
    >
    <div class="video-card-body">
      <h3 :title="titleOf(video)">{{ titleOf(video) }}</h3>
      <div class="video-score-row">
        <span class="score-caption">综合得分</span
        ><strong v-if="score !== null" class="video-score"
          >{{ score.toFixed(2) }}<small>分</small></strong
        ><span v-else class="collecting-label">数据采集中</span
        ><PhSparkle
          v-if="isHighScore(video)"
          class="high-sparkle"
          aria-label="高分视频"
        />
      </div>
      <dl class="video-metrics">
        <div
          v-for="[field, label, icon] in metrics"
          :key="field"
          :title="`${label}：${video[field] ?? '暂无数据'}`"
        >
          <dt>
            <component :is="icon" aria-hidden="true" /><span>{{ label }}</span>
          </dt>
          <dd>{{ formatCount(video[field]) }}</dd>
        </div>
      </dl>
      <footer class="video-credits">
        <strong :title="video.up_name">{{
          video.up_name || "未知 UP 主"
        }}</strong
        ><span v-if="video.director" :title="video.director"
          >编导 · {{ video.director }}</span
        ><span v-else>编导未填写</span>
      </footer>
    </div>
  </GlassPanel>
</template>
