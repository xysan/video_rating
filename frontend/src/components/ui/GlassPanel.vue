<script setup>
defineProps({ as: { type: String, default: "section" } });
</script>
<template>
  <component :is="as" class="glass-panel"><slot /></component>
</template>
