<script setup>
import { PhPlay, PhHeart, PhCoins, PhStar, PhChatCircle } from "@phosphor-icons/vue";
import { formatCount } from "../../utils/dashboard";
defineProps({ video: Object });
const metrics = [
  ["play_count", "播放", PhPlay],
  ["interact_rate", "互动率", PhStar],
  ["comment_count", "评论", PhChatCircle],
  ["coin_count", "投币", PhCoins],
  ["like_count", "点赞", PhHeart],
];
</script>
<template><dl class="video-metrics">
        <div
          v-for="[field, label, icon] in metrics"
          :key="field"
          :title="`${label}：${video[field] ?? '暂无数据'}`"
        >
          <dt>
            <component :is="icon" aria-hidden="true" /><span>{{ label }}</span>
          </dt>
          <dd>{{ field === "interact_rate" ? (video[field] == null ? "—" : (video[field]*100).toFixed(2)+"%") : formatCount(video[field]) }}</dd>
        </div>
      </dl></template>