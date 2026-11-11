<script setup>
import ToastHost from "./components/ui/ToastHost.vue";
import "./styles/data-pages.css";
</script>
<template>
  <div class="ambient-background" aria-hidden="true">
    <div class="ambient-orb orb-purple" />
    <div class="ambient-orb orb-cyan" />
    <div class="ambient-orb orb-pink" />
  </div>
  <RouterView />
  <ToastHost />
</template>
