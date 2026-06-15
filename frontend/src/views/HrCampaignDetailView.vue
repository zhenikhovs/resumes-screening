<script setup>
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { api } from '../api/client'
import { friendlyError } from '../utils/userMessages'

const route = useRoute()
const id = computed(() => route.params.id)

const campaign = ref(null)
const candidates = ref([])
const results = ref(null)
const error = ref('')
const inviteEmails = ref({})
const selectedForInvite = ref([])
const invitationsSent = ref([])
const activeTab = ref('candidates')
const showRankingDebug = ref(false)
const rankingDebug = ref(null)
const rankingDebugLoading = ref(false)
const scenarioFile = ref(null)
const uploadingScenario = ref(false)
const scenarioSaved = ref('')
const reprocessingId = ref(null)
const expandedTranscripts = ref({})
const TRANSCRIPT_PREVIEW_LEN = 220

let pollTimer = null

function transcriptKey(interviewId, questionId) {
  return `${interviewId}:${questionId}`
}

function isTranscriptExpanded(interviewId, questionId) {
  return !!expandedTranscripts.value[transcriptKey(interviewId, questionId)]
}

function toggleTranscript(interviewId, questionId) {
  const key = transcriptKey(interviewId, questionId)
  expandedTranscripts.value[key] = !expandedTranscripts.value[key]
}

function transcriptDisplay(text, interviewId, questionId) {
  if (!text) return ''
  if (isTranscriptExpanded(interviewId, questionId) || text.length <= TRANSCRIPT_PREVIEW_LEN) {
    return text
  }
  return `${text.slice(0, TRANSCRIPT_PREVIEW_LEN)}…`
}

function transcriptCanExpand(text) {
  return !!text && text.length > TRANSCRIPT_PREVIEW_LEN
}

const steps = computed(() => {
  const s = campaign.value?.status
  return [
    { key: 'collecting', label: '1. Загрузка с hh.ru', done: ['preparing', 'ranking', 'ranked'].includes(s) },
    { key: 'preparing', label: '2. Подготовка', done: ['ranking', 'ranked'].includes(s) },
    { key: 'ranking', label: '3. Сравнение с вакансией', done: s === 'ranked' },
    { key: 'ranked', label: '4. Готово', done: s === 'ranked' },
  ]
})

const lastJobError = computed(() => {
  const jobs = campaign.value?.jobs
  if (!jobs?.length) return ''
  const failed = jobs.find((j) => j.status === 'failed' && j.error_message)
  const raw = failed?.error_message || jobs[0]?.error_message || ''
  return friendlyError(raw)
})

async function load() {
  try {
    campaign.value = await api(`/api/campaigns/${id.value}`)
    if (campaign.value.status === 'ranked') {
      candidates.value = await api(`/api/campaigns/${id.value}/candidates`)
      for (const c of candidates.value) {
        if (c.invited_email) inviteEmails.value[c.resume_id] = c.invited_email
      }
      results.value = await api(`/api/campaigns/${id.value}/results`)
    } else {
      candidates.value = []
    }
  } catch (e) {
    error.value = friendlyError(e.message)
  }
}

function startPoll() {
  pollTimer = setInterval(() => {
    if (campaign.value && !['ranked', 'failed'].includes(campaign.value.status)) load()
  }, 2500)
}

function setEmail(resumeId, val) {
  inviteEmails.value[resumeId] = val
}

function toggleSelect(resumeId) {
  const i = selectedForInvite.value.indexOf(resumeId)
  if (i >= 0) selectedForInvite.value.splice(i, 1)
  else selectedForInvite.value.push(resumeId)
}

async function sendInvites() {
  const resume_ids = selectedForInvite.value
  const emails = resume_ids.map((rid) => inviteEmails.value[rid]).filter(Boolean)
  if (resume_ids.length !== emails.length) {
    error.value = 'Укажите email для каждого выбранного кандидата'
    return
  }
  error.value = ''
  try {
    invitationsSent.value = await api(`/api/campaigns/${id.value}/invitations`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ resume_ids, emails }),
    })
    await load()
  } catch (e) {
    error.value = friendlyError(e.message)
  }
}

async function loadRankingDebug() {
  if (rankingDebug.value || rankingDebugLoading.value) return
  rankingDebugLoading.value = true
  error.value = ''
  try {
    rankingDebug.value = await api(`/api/campaigns/${id.value}/ranking-debug`)
  } catch (e) {
    error.value = friendlyError(e.message)
  } finally {
    rankingDebugLoading.value = false
  }
}

function toggleRankingDebug() {
  showRankingDebug.value = !showRankingDebug.value
  if (showRankingDebug.value) loadRankingDebug()
}

async function uploadScenario() {
  if (!scenarioFile.value?.files?.length) return
  uploadingScenario.value = true
  error.value = ''
  scenarioSaved.value = ''
  try {
    const fd = new FormData()
    fd.append('file', scenarioFile.value.files[0])
    const res = await api(`/api/campaigns/${id.value}/scenario`, { method: 'POST', body: fd })
    const n = res?.questions_count
    scenarioSaved.value =
      typeof n === 'number' ? `Сохранено: ${n} вопросов` : 'Сохранено'
    await load()
    activeTab.value = 'scenario'
  } catch (e) {
    error.value = friendlyError(e.message)
  } finally {
    uploadingScenario.value = false
  }
}

async function reprocessInterview(interviewId) {
  reprocessingId.value = interviewId
  error.value = ''
  try {
    await api(`/api/campaigns/${id.value}/interviews/${interviewId}/reprocess`, { method: 'POST' })
    setTimeout(async () => {
      if (campaign.value?.status === 'ranked') {
        results.value = await api(`/api/campaigns/${id.value}/results`)
      }
      reprocessingId.value = null
    }, 1500)
  } catch (e) {
    error.value = friendlyError(e.message)
    reprocessingId.value = null
  }
}

const interviewStatusHint = {
  pending: 'Кандидат ещё не начал собеседование.',
  in_progress: 'Кандидат проходит собеседование.',
  processing: 'Ответы обрабатываются — балл и отзывы появятся после завершения.',
  failed: 'Обработка завершилась с ошибкой. Балл не рассчитан.',
}

onMounted(() => {
  load()
  startPoll()
})
onUnmounted(() => clearInterval(pollTimer))
</script>

<template>
  <div class="container">
    <router-link to="/">← Все кампании</router-link>
    <h1 class="page-title" style="margin-top: 1rem">
      {{ campaign?.title || campaign?.vacancy_title }}
    </h1>
    <p class="page-sub">
      <template v-if="campaign?.title && campaign?.vacancy_title && campaign.title !== campaign.vacancy_title">
        Вакансия на hh.ru: {{ campaign.vacancy_title }} ·
      </template>
      <template
        v-if="
          campaign?.search_text &&
          campaign.search_text !== campaign?.vacancy_title &&
          campaign.search_text !== campaign?.title
        "
      >
        Поиск резюме: «{{ campaign.search_text }}» ·
      </template>
      <span v-if="campaign?.demo_mode" class="badge badge-warn">учебный режим (без hh.ru)</span>
    </p>

    <div v-if="campaign" class="steps">
      <span
        v-for="st in steps"
        :key="st.key"
        class="step"
        :class="{ active: campaign.status === st.key, done: st.done }"
      >
        {{ st.label }}
      </span>
    </div>

    <p v-if="error" class="error">{{ error }}</p>

    <div v-if="campaign?.status === 'failed'" class="card" style="border-color: #fca5a5; background: #fef2f2">
      <h2 style="color: #991b1b">Подбор не завершился</h2>
      <p v-if="lastJobError" style="margin-bottom: 0.75rem; color: #991b1b">{{ lastJobError }}</p>
      <p class="hint" style="margin-bottom: 0">
        Список кандидатов появится только когда дойдёт до шага «Готово».
        <router-link to="/">Запустите новый подбор</router-link> с той же или другой вакансией.
      </p>
    </div>

    <p v-else-if="campaign?.status !== 'ranked'" class="hint">
      Подождите, идёт обработка. Страница обновляется сама. Когда загорится шаг «Готово», здесь появятся
      лучшие кандидаты (обычно 5 человек).
    </p>

    <div v-if="campaign" class="tabs">
      <button class="tab" :class="{ active: activeTab === 'candidates' }" @click="activeTab = 'candidates'">
        Кандидаты
      </button>
      <button class="tab" :class="{ active: activeTab === 'scenario' }" @click="activeTab = 'scenario'">
        Сценарий интервью
      </button>
      <button class="tab" :class="{ active: activeTab === 'results' }" @click="activeTab = 'results'">
        Результаты
      </button>
    </div>

    <div
      v-if="activeTab === 'candidates' && campaign?.status !== 'ranked' && campaign?.status !== 'failed'"
      class="card"
    >
      <p class="hint" style="margin: 0">Здесь появятся кандидаты, когда подбор дойдёт до шага «Готово».</p>
    </div>

    <div v-if="activeTab === 'candidates' && campaign?.status === 'ranked'" class="card">
      <h2>Лучшие кандидаты</h2>
      <p class="hint">Отметьте тех, кого хотите пригласить на видео-интервью, и укажите email.</p>
      <table>
        <thead>
          <tr>
            <th></th>
            <th>Место</th>
            <th>Должность</th>
            <th>Кратко о резюме</th>
            <th>Email для приглашения</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="c in candidates" :key="c.resume_id">
            <td>
              <input
                type="checkbox"
                :checked="selectedForInvite.includes(c.resume_id)"
                @change="toggleSelect(c.resume_id)"
              />
            </td>
            <td>{{ c.rank }}</td>
            <td class="candidate-title">{{ c.position || c.title }}</td>
            <td class="candidate-summary">{{ c.summary || '—' }}</td>
            <td>
              <input
                :value="inviteEmails[c.resume_id] || ''"
                placeholder="email@example.com"
                @input="setEmail(c.resume_id, $event.target.value)"
              />
              <span v-if="c.invited" class="badge badge-ok" style="margin-left: 0.35rem">уже приглашён</span>
            </td>
          </tr>
        </tbody>
      </table>
      <p v-if="!candidates.length" class="hint">
        Подбор завершён, но подходящих кандидатов не осталось. Попробуйте другую поисковую фразу или вакансию.
      </p>
      <button
        class="btn btn-primary"
        style="margin-top: 1rem"
        :disabled="!selectedForInvite.length"
        @click="sendInvites"
      >
        Отправить / повторить приглашение
      </button>

      <button
        type="button"
        class="btn btn-secondary ranking-debug-toggle"
        style="margin-top: 1.25rem"
        @click="toggleRankingDebug"
      >
        {{ showRankingDebug ? 'Скрыть' : 'Показать' }} технические детали ранжирования (E5 и rerank)
      </button>
      <div v-if="showRankingDebug" class="ranking-debug-body">
          <p v-if="rankingDebugLoading" class="hint">Загрузка…</p>
          <template v-else-if="rankingDebug">
            <p v-if="rankingDebug.note" class="hint">{{ rankingDebug.note }}</p>
            <p v-else class="hint">
              Сначала отбор по E5 (score_norm, min-max внутри пула). Затем уточнение cross-encoder
              (rerank_score) — итоговый порядок в таблице выше совпадает с блоком rerank. У лидера E5
              не обязательно 1.0 после пересортировки.
            </p>
            <p v-if="rankingDebug.threshold != null" class="hint">
              Порог score_norm (90-й перцентиль): {{ rankingDebug.threshold }}
            </p>
            <h3>Этап 1 — E5 (до rerank)</h3>
            <table class="ranking-debug-table">
              <thead>
                <tr>
                  <th>#</th>
                  <th>Должность</th>
                  <th>similarity</th>
                  <th>score_norm</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="r in rankingDebug.e5_stage" :key="'e5-' + r.resume_id">
                  <td>{{ r.rank }}</td>
                  <td>{{ r.position }}</td>
                  <td>{{ r.similarity_score ?? '—' }}</td>
                  <td>{{ r.score_norm ?? '—' }}</td>
                </tr>
              </tbody>
            </table>
            <h3 style="margin-top: 1.25rem">Этап 2 — rerank (итоговый порядок)</h3>
            <table class="ranking-debug-table">
              <thead>
                <tr>
                  <th>#</th>
                  <th>Должность</th>
                  <th>score_norm (E5)</th>
                  <th>rerank_score</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="r in rankingDebug.rerank_stage" :key="'rr-' + r.resume_id">
                  <td>{{ r.rank }}</td>
                  <td>{{ r.position }}</td>
                  <td>{{ r.score_norm ?? '—' }}</td>
                  <td>{{ r.rerank_score ?? '—' }}</td>
                </tr>
              </tbody>
            </table>
          </template>
      </div>
    </div>

    <div v-if="activeTab === 'scenario'" class="card">
      <h2>Вопросы для видео-интервью</h2>
      <p v-if="campaign && !campaign.scenario?.loaded" class="hint">
        Сценарий не найден — загрузите файл с вопросами.
      </p>
      <label>Файл с вопросами</label>
      <input ref="scenarioFile" type="file" accept=".json,application/json" />
      <button class="btn btn-secondary" :disabled="uploadingScenario" @click="uploadScenario">
        {{ uploadingScenario ? 'Загрузка…' : 'Загрузить вопросы' }}
      </button>
      <p v-if="scenarioSaved" class="badge badge-ok" style="margin-top: 0.75rem">{{ scenarioSaved }}</p>
    </div>

    <div v-if="invitationsSent.length" class="card success">
      <h3>Приглашения созданы</h3>
      <table>
        <thead>
          <tr>
            <th>Email</th>
            <th>Ссылка</th>
            <th>Пароль</th>
            <th>Почта</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="inv in invitationsSent" :key="inv.id">
            <td>{{ inv.email }}</td>
            <td>
              <a v-if="inv.invite_path" :href="inv.invite_path" target="_blank" rel="noopener">
                {{ inv.invite_path }}
              </a>
            </td>
            <td><code>{{ inv.temp_password }}</code></td>
            <td>
              <span v-if="inv.email_sent" class="badge badge-ok">письмо отправлено</span>
              <span v-else class="badge badge-warn">письмо не настроено — пароль в журнале приглашений</span>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <div v-if="activeTab === 'results'" class="card">
      <h2>Результаты видео-собеседований</h2>
      <p v-if="!results?.interviews?.length" class="hint">Пока нет интервью по этой кампании</p>
      <div v-for="iv in results?.interviews || []" :key="iv.interview_id" class="card card-nested">
        <h3>{{ iv.candidate_email }}</h3>
        <p class="hint" style="margin-bottom: 0.5rem">Резюме: {{ iv.resume_id }}</p>
        <p class="interview-result-line">
          <template v-if="iv.status === 'completed' && iv.score_avg != null">
            <span>Средний балл: <strong>{{ iv.score_avg }}</strong></span>
            <span v-if="iv.approved === true" class="badge badge-ok">прошёл</span>
            <span v-else-if="iv.approved === false" class="badge badge-fail">не прошёл</span>
          </template>
          <template v-else>
            <span class="hint">{{ interviewStatusHint[iv.status] || 'Статус: ' + iv.status }}</span>
            <span v-if="iv.status === 'processing'" class="badge badge-info">обработка</span>
            <span v-else-if="iv.status === 'failed'" class="badge badge-fail">ошибка</span>
            <span v-else-if="iv.status === 'in_progress'" class="badge badge-info">в процессе</span>
            <span v-else-if="iv.status === 'pending'" class="badge badge-info">ожидает</span>
          </template>
        </p>

        <h4 style="margin: 1rem 0 0.5rem; font-size: 1rem">Отзывы по вопросам</h4>
        <p v-if="iv.error_message" class="error" style="margin-top: 0.5rem">{{ iv.error_message }}</p>
        <p v-if="iv.status === 'failed'" style="margin-top: 0.5rem">
          <button
            class="btn btn-secondary"
            type="button"
            :disabled="reprocessingId === iv.interview_id"
            @click="reprocessInterview(iv.interview_id)"
          >
            {{ reprocessingId === iv.interview_id ? 'Запуск…' : 'Пересчитать с видео (аудио + текст + оценка)' }}
          </button>
        </p>
        <p v-if="!iv.questions?.length" class="hint">
          <template v-if="iv.status === 'failed' && !iv.error_message">
            Отзывы недоступны — не удалось обработать ответы.
          </template>
          <template v-else-if="iv.status === 'completed'">Нет оценок по вопросам.</template>
          <template v-else>Отзывы появятся после завершения обработки ответов.</template>
        </p>
        <table v-else class="results-questions-table">
          <thead>
            <tr>
              <th>Вопрос</th>
              <th>Ответ (транскрипт)</th>
              <th>Балл</th>
              <th>Краткий отзыв</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="q in iv.questions" :key="q.question_id">
              <td class="results-q-text">{{ q.question }}</td>
              <td class="results-q-transcript">
                <template v-if="q.transcript">
                  <p class="results-transcript-body">
                    {{ transcriptDisplay(q.transcript, iv.interview_id, q.question_id) }}
                  </p>
                  <button
                    v-if="transcriptCanExpand(q.transcript)"
                    type="button"
                    class="btn-link"
                    @click="toggleTranscript(iv.interview_id, q.question_id)"
                  >
                    {{
                      isTranscriptExpanded(iv.interview_id, q.question_id)
                        ? 'Свернуть'
                        : 'Развернуть полностью'
                    }}
                  </button>
                </template>
                <span v-else class="hint">—</span>
              </td>
              <td class="results-q-score">{{ q.score ?? '—' }}</td>
              <td class="results-q-feedback">{{ q.feedback || '—' }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>

<style scoped>
.interview-result-line {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.5rem 0.75rem;
}
.results-questions-table td {
  vertical-align: top;
}
.results-q-text {
  max-width: 32%;
}
.results-q-score {
  width: 4.5rem;
  text-align: center;
  white-space: nowrap;
}
.results-q-feedback {
  line-height: 1.45;
}
.results-q-transcript {
  max-width: 36%;
}
.results-transcript-body {
  margin: 0;
  line-height: 1.45;
  white-space: pre-wrap;
  word-break: break-word;
}
.btn-link {
  margin-top: 0.35rem;
  padding: 0;
  border: none;
  background: none;
  color: var(--primary);
  font-size: 0.85rem;
  cursor: pointer;
  text-decoration: underline;
}
</style>
