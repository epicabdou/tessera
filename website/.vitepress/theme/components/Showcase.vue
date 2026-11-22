<script setup lang="ts">
import { ref } from 'vue'
import { withBase } from 'vitepress'

// Real screenshots, made by scripts/screenshots.py from the real app and backend.
const shots = [
  { id: 'merge', label: 'Merge PDF', caption: 'Put PDFs in order, choose pages from each, merge. Your folders and a live preview stay beside the tool.' },
  { id: 'convert-jpg', label: 'Convert to JPG', caption: 'Turn iPhone HEIC, PNG and WebP photos into JPG in one go. Each result shows where it was saved.' },
  { id: 'photo-editor', label: 'Photo editor', caption: 'Looks, light and colour, text, drawings, arrows and logos, all undoable.' },
  { id: 'watermark', label: 'Watermark', caption: 'The preview shows exactly what will be saved, before you save it.' },
  { id: 'organize', label: 'Organize pages', caption: 'Drag pages into order; rotate, duplicate, delete or insert them.' },
  { id: 'history', label: 'History', caption: 'Every file Tessera made, searchable, with the files it came from.' },
  { id: 'merge-light', label: 'Light theme', caption: 'Light or dark, following your Windows setting.' },
]
const active = ref(0)
</script>

<template>
  <section class="showcase" aria-label="Screenshots">
    <div class="tabs" role="tablist">
      <button
        v-for="(s, i) in shots"
        :key="s.id"
        type="button"
        role="tab"
        :aria-selected="i === active"
        :class="{ on: i === active }"
        @click="active = i"
      >
        {{ s.label }}
      </button>
    </div>
    <figure>
      <div class="frame">
        <img
          v-for="(s, i) in shots"
          v-show="i === active"
          :key="s.id"
          :src="withBase(`/screenshots/${s.id}.webp`)"
          :alt="`Tessera, ${s.label}`"
          width="1440"
          height="900"
          :loading="i === 0 ? 'eager' : 'lazy'"
        />
      </div>
      <figcaption>{{ shots[active].caption }}</figcaption>
    </figure>
  </section>
</template>

<style scoped>
.showcase {
  margin: 8px auto 0;
  max-width: 1152px;
}

.tabs {
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  gap: 6px;
  margin-bottom: 18px;
}

.tabs button {
  padding: 7px 14px;
  border: 1px solid var(--vp-c-divider);
  border-radius: 999px;
  color: var(--vp-c-text-2);
  font-size: 14px;
  font-weight: 500;
  transition: color 0.15s, border-color 0.15s, background 0.15s;
}

.tabs button:hover {
  color: var(--vp-c-text-1);
}

.tabs button.on {
  border-color: transparent;
  background: var(--vp-c-brand-soft);
  color: var(--vp-c-brand-1);
}

figure {
  margin: 0;
}

.frame {
  overflow: hidden;
  border: 1px solid var(--vp-c-divider);
  border-radius: 16px;
  background: #0b0e1c;
  box-shadow: 0 30px 80px -30px rgba(40, 30, 120, 0.55);
  aspect-ratio: 16 / 10;
}

.frame img {
  display: block;
  width: 100%;
  height: auto;
}

figcaption {
  margin-top: 14px;
  color: var(--vp-c-text-2);
  font-size: 15px;
  text-align: center;
}
</style>
