<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { api } from '../api/client'

const route = useRoute()
const inviteToken = computed(() => route.params.token)

const session = ref(null)
const error = ref('')
const uploading = ref(false)
const done = ref(false)
const videoPreview = ref(null)

const currentQuestion = computed(() => {
  if (!session.value?.questions?.length) return null
  const idx = Math.min(session.value.current_index, session.value.questions.length - 1)
  return session.value.questions[idx]
})

const progressPct = computed(() => {
  if (!session.value?.total_questions) return 0
  return Math.round((session.value.current_index / session.value.total_questions) * 100)
})

const mediaStream = ref(null)
const mediaRecorder = ref(null)
const chunks = ref([])
const recording = ref(false)

async function loadSession() {
  session.value = await api(`/api/i/${encodeURIComponent(inviteToken.value)}`)
}

async function startCamera() {
  stopCamera()
  const stream = await navigator.mediaDevices.getUserMedia({ video: true, audio: true })
  mediaStream.value = stream
  if (videoPreview.value) videoPreview.value.srcObject = stream
}

function stopCamera() {
  mediaStream.value?.getTracks().forEach((t) => t.stop())
  mediaStream.value = null
}

function startRecording() {
  chunks.value = []
  const rec = new MediaRecorder(mediaStream.value, { mimeType: 'video/webm' })
  mediaRecorder.value = rec
  rec.ondataavailable = (e) => {
    if (e.data.size) chunks.value.push(e.data)
  }
  rec.start()
  recording.value = true
}

function stopRecording() {
  return new Promise((resolve) => {
    const rec = mediaRecorder.value
    if (!rec) {
      resolve(null)
      return
    }
    rec.onstop = () => {
      recording.value = false
      resolve(new Blob(chunks.value, { type: 'video/webm' }))
    }
    rec.stop()
  })
}

async function uploadAnswer() {
  if (!currentQuestion.value) return
  error.value = ''
  uploading.value = true
  try {
    const blob = await stopRecording()
    stopCamera()
    if (!blob?.size) throw new Error('Запись пуста. Нажмите «Запись» и ответьте на вопрос.')
    const fd = new FormData()
    fd.append('file', blob, `${currentQuestion.value.question_id}.webm`)
    await api(
      `/api/i/${encodeURIComponent(inviteToken.value)}/questions/${currentQuestion.value.question_id}/video`,
      {
      method: 'POST',
      body: fd,
      },
    )
    await loadSession()
    if (session.value.current_index >= session.value.total_questions) await complete()
  } catch (e) {
    error.value = e.message
  } finally {
    uploading.value = false
  }
}

async function complete() {
  const res = await api(`/api/i/${encodeURIComponent(inviteToken.value)}/complete`, { method: 'POST' })
  done.value = true
  session.value.status = 'processing'
  alert(res.message)
}

async function init() {
  error.value = ''
  session.value = null
  done.value = false
  try {
    await loadSession()
  } catch (e) {
    error.value = e.message
  }
}

onMounted(init)
watch(inviteToken, init)
</script>

<template>
  <div class="container">
    <h1 class="page-title">Видео-собеседование</h1>
    <p v-if="session?.vacancy_title" class="page-sub">Вакансия: {{ session.vacancy_title }}</p>

    <div v-if="session" class="card">
      <div style="display: flex; justify-content: space-between; margin-bottom: 1rem">
        <span>Вопрос {{ Math.min(session.current_index + 1, session.total_questions) }} из {{ session.total_questions }}</span>
        <span>{{ progressPct }}%</span>
      </div>
      <div
        style="height: 6px; background: var(--surface2); border-radius: 4px; margin-bottom: 1.25rem; overflow: hidden"
      >
        <div :style="{ width: progressPct + '%', height: '100%', background: 'var(--primary)' }" />
      </div>
    </div>

    <div v-if="session?.status === 'completed' || session?.status === 'processing'" class="card">
      <p class="success">
        Спасибо, видео-собеседование завершено. Ваши ответы переданы специалистам для рассмотрения.
        При положительном решении с вами свяжутся по контактам из приглашения.
      </p>
    </div>

    <div v-else-if="currentQuestion && !done" class="card">
      <h2>{{ currentQuestion.question }}</h2>
      <video ref="videoPreview" class="preview" autoplay muted playsinline />
      <div style="margin-top: 1rem; display: flex; gap: 0.5rem; flex-wrap: wrap">
        <button class="btn btn-secondary" @click="startCamera">1. Включить камеру</button>
        <button class="btn btn-secondary" :disabled="!mediaStream || recording" @click="startRecording">
          2. Запись
        </button>
        <button class="btn btn-primary" :disabled="uploading || !mediaRecorder" @click="uploadAnswer">
          {{ uploading ? 'Сохранение…' : '3. Следующий вопрос →' }}
        </button>
      </div>
      <p v-if="recording" class="badge badge-fail" style="margin-top: 0.75rem">● Идёт запись</p>
    </div>

    <p v-if="error" class="error">{{ error }}</p>
  </div>
</template>
