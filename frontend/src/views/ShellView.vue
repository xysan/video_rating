<script setup>
import { useRoute } from "vue-router";
const route = useRoute();
</script>
<template>
  <section class="shell-view">
    <p class="eyebrow">{{ route.meta.english }}</p>
    <h1>{{ route.meta.title }}</h1>
  </section>
</template>
