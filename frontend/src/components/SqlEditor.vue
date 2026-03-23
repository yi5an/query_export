<template>
  <div class="editor-wrap">
    <Codemirror v-model="value" :extensions="extensions" :style="{ height }" />
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { Codemirror } from 'vue-codemirror'
import { sql } from '@codemirror/lang-sql'

const props = withDefaults(
  defineProps<{
    modelValue: string
    height?: string
  }>(),
  {
    height: '280px'
  }
)

const emit = defineEmits<{
  (event: 'update:modelValue', value: string): void
}>()

const value = computed({
  get: () => props.modelValue,
  set: (nextValue: string) => emit('update:modelValue', nextValue)
})

const extensions = [sql()]
</script>

<style scoped>
.editor-wrap {
  overflow: hidden;
  border: 1px solid #d9e5f1;
  border-radius: 14px;
}

:deep(.cm-editor) {
  font-size: 14px;
}
</style>
