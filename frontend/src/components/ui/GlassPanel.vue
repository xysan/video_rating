<script setup>
defineProps({
  as: { type: String, default: "section" },
  blur: { type: Boolean, default: true },
});
</script>
<template>
  <component :is="as" class="glass-panel" :class="{ 'glass-panel-flat': !blur }"
    ><slot
  /></component>
</template>
