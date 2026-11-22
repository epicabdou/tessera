<script setup lang="ts">
import { withBase } from 'vitepress'
import { CATEGORIES, docsLink } from '../tools'

const sections = (['Documents', 'Images'] as const).map((name) => ({ name, categories: CATEGORIES.filter((c) => c.section === name) }))
</script>

<template>
  <div class="grid-wrap">
    <section v-for="s in sections" :key="s.name" class="section">
      <h3>{{ s.name === 'Documents' ? 'PDF & documents' : 'Images & photos' }}</h3>
      <div class="cats">
        <div v-for="c in s.categories" :key="c.id" class="cat">
          <a class="cat-name" :href="withBase(docsLink(c))">{{ c.label }}</a>
          <ul>
            <li v-for="t in c.tools" :key="t.id">
              <a :href="withBase(docsLink(c, t))" :title="t.hint">
                <strong>{{ t.label }}</strong>
                <span>{{ t.hint }}</span>
              </a>
            </li>
          </ul>
        </div>
      </div>
    </section>
  </div>
</template>

<style scoped>
.grid-wrap {
  display: flex;
  flex-direction: column;
  gap: 40px;
}

.section h3 {
  margin: 0 0 16px;
  font-size: 20px;
  font-weight: 700;
}

.cats {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
  gap: 16px;
}

.cat {
  padding: 18px 18px 12px;
  border: 1px solid var(--vp-c-divider);
  border-radius: 14px;
  background: var(--vp-c-bg-soft);
}

.cat-name {
  display: block;
  margin-bottom: 8px;
  color: var(--vp-c-text-2);
  font-size: 12px;
  font-weight: 600;
  letter-spacing: 0.5px;
  text-decoration: none;
  text-transform: uppercase;
}

.cat-name:hover {
  color: var(--vp-c-brand-1);
}

ul {
  margin: 0;
  padding: 0;
  list-style: none;
}

li a {
  display: flex;
  flex-direction: column;
  padding: 7px 8px;
  margin: 0 -8px;
  border-radius: 8px;
  color: inherit;
  text-decoration: none;
  transition: background 0.15s;
}

li a:hover {
  background: var(--vp-c-default-soft);
}

li strong {
  font-size: 15px;
  font-weight: 600;
}

li a:hover strong {
  color: var(--vp-c-brand-1);
}

li span {
  color: var(--vp-c-text-2);
  font-size: 13px;
  line-height: 1.4;
}
</style>
