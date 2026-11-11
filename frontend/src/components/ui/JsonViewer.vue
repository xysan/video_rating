<script setup>
import { computed } from "vue";
const props = defineProps({ value: { default: null } });
// 使用文本节点渲染 JSON，绝不把原始字段作为 HTML 注入。
const tokens = computed(() => {
  const text = JSON.stringify(props.value, null, 2) ?? "null";
  const pattern =
    /("(?:\\.|[^"\\])*"\s*:|"(?:\\.|[^"\\])*"|\b(?:true|false|null)\b|-?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?)/g;
  const result = [];
  let start = 0;
  for (const match of text.matchAll(pattern)) {
    result.push({ text: text.slice(start, match.index), type: "plain" });
    const value = match[0];
    result.push({
      text: value,
      type: value.endsWith(":")
        ? "key"
        : value.startsWith('"')
          ? "string"
          : /true|false|null/.test(value)
            ? "literal"
            : "number",
    });
    start = match.index + value.length;
  }
  result.push({ text: text.slice(start), type: "plain" });
  return result;
});
</script>
<template>
  <pre
    class="json-viewer"
    tabindex="0"
    aria-label="格式化 JSON"
  ><code><span v-for="(token,index) in tokens" :key="index" :class="`json-${token.type}`">{{ token.text }}</span></code></pre>
</template>
