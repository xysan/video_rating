<script setup>
import { ref, watch, nextTick, onBeforeUnmount } from "vue";
import { toastTarget } from "./toast";
const props = defineProps({ open: Boolean, title: String, busy: Boolean });
const emit = defineEmits(["close"]);
const dialog = ref(null);
let previousFocus;
watch(
  () => props.open,
  async (value) => {
    await nextTick();
    if (value) {
      previousFocus = document.activeElement;
      toastTarget.value = dialog.value;
      if (!dialog.value.open) dialog.value.showModal();
    } else {
      toastTarget.value = null;
      dialog.value?.close();
      previousFocus?.focus?.();
    }
  },
);
onBeforeUnmount(() => {
  toastTarget.value = null;
  dialog.value?.close();
});
</script>
<template>
  <dialog
    ref="dialog"
    class="app-dialog"
    aria-labelledby="dialog-title"
    @cancel.prevent="!busy && emit('close')"
    @click="
      (event) => {
        if (event.target === dialog && !busy) emit('close');
      }
    "
  >
    <header>
      <h2 id="dialog-title">{{ title }}</h2>
      <button
        class="dialog-close"
        aria-label="关闭弹窗"
        :disabled="busy"
        @click="emit('close')"
      >
        ×
      </button>
    </header>
    <div class="dialog-content"><slot /></div>
    <footer v-if="$slots.footer" class="dialog-footer">
      <slot name="footer" />
    </footer>
  </dialog>
</template>
