<script setup>
import { ref, computed } from "vue";
import { PhEye, PhEyeSlash } from "@phosphor-icons/vue";
defineOptions({ inheritAttrs: false });
const props = defineProps({
  modelValue: String,
  label: String,
  id: { type: String, required: true },
  type: { type: String, default: "text" },
  error: Boolean,
});
defineEmits(["update:modelValue"]);
const revealed = ref(false);
const inputType = computed(() =>
  props.type === "password" && revealed.value ? "text" : props.type,
);
</script>
<template>
  <div class="input-group">
    <label :for="id">{{ label }}</label>
    <div class="input-wrap" :class="{ 'input-error': error }">
      <span class="input-icon" aria-hidden="true"><slot name="icon" /></span
      ><input
        v-bind="$attrs"
        :id="id"
        :type="inputType"
        :value="modelValue"
        :aria-invalid="error"
        @input="$emit('update:modelValue', $event.target.value)"
      /><button
        v-if="type === 'password'"
        class="reveal-button"
        type="button"
        :aria-label="revealed ? '隐藏密码' : '显示密码'"
        :aria-pressed="revealed"
        @click="revealed = !revealed"
      >
        <PhEyeSlash v-if="revealed" /><PhEye v-else />
      </button>
    </div>
  </div>
</template>
