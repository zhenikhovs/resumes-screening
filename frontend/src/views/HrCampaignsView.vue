<script setup>
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { api } from '../api/client'
import { friendlyError } from '../utils/userMessages'

const router = useRouter()
const campaigns = ref([])
const loading = ref(false)
const error = ref('')
const creating = ref(false)

const form = ref({
  hh_url: '',
  search_text: 'Junior PHP разработчик',
  title: 'Junior PHP разработчик для Магистерской диссертации',
})

function campaignRow(c) {
  const name = c.title || c.vacancy_title || '—'
  const details = []
  if (c.title && c.vacancy_title && c.title !== c.vacancy_title) {
    details.push(`Вакансия: ${c.vacancy_title}`)
  }
  if (
    c.search_text &&
    c.search_text !== c.vacancy_title &&
    c.search_text !== c.title
  ) {
    details.push(`Поиск: ${c.search_text}`)
  }
  return { name, details }
}

const statusLabel = {
  collecting: 'Загружаем вакансию и резюме',
  preparing: 'Готовим тексты',
  ranking: 'Сравниваем с вакансией',
  ranked: 'Готово',
  failed: 'Не удалось завершить',
}

async function load() {
  loading.value = true
  try {
    campaigns.value = await api('/api/campaigns')
  } catch (e) {
    error.value = friendlyError(e.message)
  } finally {
    loading.value = false
  }
}

async function create() {
  error.value = ''
  creating.value = true
  try {
    const c = await api('/api/campaigns', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(form.value),
    })
    router.push(`/campaigns/${c.id}`)
  } catch (e) {
    error.value = friendlyError(e.message)
  } finally {
    creating.value = false
  }
}

onMounted(load)
</script>

<template>
  <div class="container">
    <h1 class="page-title">Подбор кандидатов</h1>
    <p class="page-sub">
      Укажите вашу вакансию на hh.ru и фразу для поиска резюме — система подберёт лучших кандидатов и
      поможет пригласить их на видео-интервью.
    </p>

    <div class="card">
      <h2>Новый подбор</h2>
      <label>Ссылка на вашу вакансию на hh.ru</label>
      <input
        v-model="form.hh_url"
        placeholder="https://hh.ru/vacancy/12345678"
      />
      <p class="hint">Откройте вакансию в браузере и скопируйте адрес из строки наверху.</p>

      <label>Название подбора (для себя)</label>
      <input
        v-model="form.title"
        placeholder="Junior PHP разработчик для Магистерской диссертации"
      />
      <p class="hint">Как вы назовёте этот подбор в списке — на результат не влияет.</p>

      <label>Кого ищем на hh.ru (поисковая фраза)</label>
      <input
        v-model="form.search_text"
        placeholder="Junior PHP разработчик"
      />
      <p class="hint">
        Фраза для поиска резюме на сайте hh.ru — как в строке поиска кандидатов.
      </p>

      <p v-if="error" class="error">{{ error }}</p>
      <button class="btn btn-primary" :disabled="creating" @click="create">
        {{ creating ? 'Запуск…' : 'Запустить подбор' }}
      </button>
    </div>

    <div class="card">
      <h2>Кампании</h2>
      <p v-if="loading">Загрузка…</p>
      <table v-else-if="campaigns.length">
        <thead>
          <tr>
            <th>№</th>
            <th>Подбор</th>
            <th>Резюме</th>
            <th>Статус</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="c in campaigns" :key="c.id">
            <td>{{ c.id }}</td>
            <td>
              <div>{{ campaignRow(c).name }}</div>
              <div
                v-for="(line, i) in campaignRow(c).details"
                :key="i"
                class="hint"
                style="margin: 0.15rem 0 0"
              >
                {{ line }}
              </div>
            </td>
            <td>{{ c.resumes_count }}</td>
            <td>
              <span class="badge" :class="c.status === 'ranked' ? 'badge-ok' : c.status === 'failed' ? 'badge-fail' : 'badge-info'">
                {{ statusLabel[c.status] || c.status }}
              </span>
              <span v-if="c.demo_mode" class="badge badge-warn" style="margin-left: 0.25rem">учебный режим</span>
            </td>
            <td>
              <router-link :to="`/campaigns/${c.id}`">Открыть →</router-link>
            </td>
          </tr>
        </tbody>
      </table>
      <p v-else class="hint">Создайте первую кампанию</p>
    </div>
  </div>
</template>
