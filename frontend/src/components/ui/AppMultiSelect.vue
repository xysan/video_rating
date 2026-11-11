<script setup>
import { ref, computed, onMounted, onBeforeUnmount } from "vue";
import { PhCaretDown, PhX, PhMagnifyingGlass } from "@phosphor-icons/vue";
const props = defineProps({
  id: { type: String, required: true },
  label: String,
  options: { type: Array, default: () => [] },
  modelValue: { type: Array, default: () => [] },
});
const emit = defineEmits(["update:modelValue"]);
const open = ref(false),
  query = ref(""),
  root = ref(null),
  trigger = ref(null);
const matches = computed(() =>
  props.options.filter((x) =>
    x.toLocaleLowerCase().includes(query.value.toLocaleLowerCase()),
  ),
);
function toggle(value) {
  emit(
    "update:modelValue",
    props.modelValue.includes(value)
      ? props.modelValue.filter((x) => x !== value)
      : [...props.modelValue, value],
  );
}
function close() {
  open.value = false;
  query.value = "";
}
function outside(e) {
  if (!root.value?.contains(e.target)) close();
}
function escape() {
  close();
  trigger.value?.focus();
}
onMounted(() => document.addEventListener("pointerdown", outside));
onBeforeUnmount(() => document.removeEventListener("pointerdown", outside));
</script>
<template>
  <div ref="root" class="multi-select" @keydown.esc.stop="escape">
    <label :id="id + '-label'">{{ label }}</label>
    <div class="multi-control" :class="{ 'is-open': open }">
      <div v-if="modelValue.length" class="selected-tags">
        <span v-for="value in modelValue" :key="value" class="selection-tag"
          ><span>{{ value }}</span
          ><button
            type="button"
            :aria-label="'移除' + value"
            @click="toggle(value)"
          >
            <PhX /></button
        ></span>
      </div>
      <button
        ref="trigger"
        class="multi-trigger"
        type="button"
        :aria-labelledby="id + '-label'"
        :aria-expanded="open"
        :aria-controls="id + '-options'"
        @click="open = !open"
        @keydown.down.prevent="open = true"
      >
        <span>{{
          modelValue.length
            ? "已选 " + modelValue.length + " 项"
            : "全部" + label
        }}</span
        ><PhCaretDown />
      </button>
    </div>
    <div v-if="open" :id="id + '-options'" class="multi-menu" @click.stop>
      <div class="multi-search">
        <PhMagnifyingGlass aria-hidden="true" /><input
          v-model="query"
          :aria-label="'搜索' + label"
          :placeholder="'搜索' + label"
        />
      </div>
      <div class="multi-options" role="group" :aria-labelledby="id + '-label'">
        <label
          v-for="(value, index) in matches"
          :key="value"
          :for="id + '-choice-' + index"
          class="multi-option"
          @pointerdown.prevent
          @click.stop.prevent="toggle(value)"
          ><input
            :id="id + '-choice-' + index"
            type="checkbox"
            :checked="modelValue.includes(value)"
            @click.stop
            @change="toggle(value)"
          /><span>{{ value }}</span></label
        >
        <p v-if="!matches.length" class="multi-empty">没有匹配选项</p>
      </div>
      <button
        v-if="modelValue.length"
        type="button"
        class="multi-clear"
        @click="emit('update:modelValue', [])"
      >
        清除已选
      </button>
    </div>
  </div>
</template>
