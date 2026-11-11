<script setup>
import { computed } from "vue";
import AppButton from "./AppButton.vue";
const props = defineProps({
  page: Number,
  pageSize: Number,
  total: Number,
  loading: Boolean,
});
defineEmits(["page", "size"]);
const pages = computed(() =>
  Math.max(1, Math.ceil(props.total / props.pageSize)),
);
</script>
<template>
  <footer class="pagination">
    <span>共 {{ total }} 条</span
    ><label
      >每页
      <select
        :value="pageSize"
        :disabled="loading"
        @change="$emit('size', Number($event.target.value))"
      >
        <option v-for="size in [10, 20, 50, 100]" :key="size" :value="size">
          {{ size }} 条
        </option>
      </select></label
    >
    <div>
      <AppButton
        variant="secondary"
        :disabled="loading || page <= 1"
        @click="$emit('page', page - 1)"
        >上一页</AppButton
      ><span aria-live="polite">{{ page }} / {{ pages }}</span
      ><AppButton
        variant="secondary"
        :disabled="loading || page >= pages"
        @click="$emit('page', page + 1)"
        >下一页</AppButton
      >
    </div>
  </footer>
</template>
