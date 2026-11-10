<script setup>
defineProps({
  variant: { type: String, default: "primary" },
  loading: Boolean,
  disabled: Boolean,
  type: { type: String, default: "button" },
});
</script>
<template>
  <button
    :type="type"
    :class="['app-button', `button-${variant}`]"
    :disabled="disabled || loading"
    :aria-busy="loading"
  >
    <span v-if="loading" class="spinner" aria-hidden="true" /><slot />
  </button>
</template>
