<script setup>
import { ref, watch } from "vue";
import { PhImage } from "@phosphor-icons/vue";
const props = defineProps({ src: String, alt: String });
const failed = ref(false);
watch(
  () => props.src,
  () => {
    failed.value = false;
  },
);
</script>
<template>
  <div class="video-cover">
    <img
      v-if="src && !failed"
      :src="src"
      :alt="alt"
      loading="lazy"
      referrerpolicy="no-referrer"
      @error="failed = true"
    />
    <div
      v-else
      class="cover-fallback"
      role="img"
      :aria-label="`${alt}，暂无封面`"
    >
      <PhImage aria-hidden="true" /><span>暂无封面</span>
    </div>
    <slot />
  </div>
</template>
