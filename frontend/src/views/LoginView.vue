<script setup>
import { onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { fetchMyInterviews, getToken } from '../api/client'
import { useAuthStore } from '../stores/auth'

const route = useRoute()
const router = useRouter()
const email = ref('')
const password = ref('')
const error = ref('')
const interviewChoices = ref([])
const auth = useAuthStore()
const skipForm = ref(false)

function isInvitePath(path) {
  return typeof path === 'string' && path.startsWith('/i/')
}

async function goAfterLogin() {
  const redirect = typeof route.query.redirect === 'string' ? route.query.redirect : ''
  if (isInvitePath(redirect)) {
    await router.replace(redirect)
    return
  }

  const list = await fetchMyInterviews()
  if (list.length === 1) {
    await router.replace(list[0].entry_path)
    return
  }
  if (list.length > 1) {
    interviewChoices.value = list
    return
  }
  error.value = 'Нет активных собеседований.'
}

async function tryAlreadyLoggedIn() {
  if (!getToken()) return false
  skipForm.value = true
  try {
    if (!auth.user) await auth.loadUser()
    if (!auth.user) return false
    if (auth.user.role === 'hr') {
      await router.replace('/')
      return true
    }
    await goAfterLogin()
    return true
  } catch (e) {
    skipForm.value = false
    error.value = e.message || 'Ошибка'
    return false
  }
}

onMounted(() => {
  tryAlreadyLoggedIn()
})

async function submit() {
  error.value = ''
  interviewChoices.value = []
  try {
    await auth.login(email.value, password.value)
    if (auth.user?.role === 'hr') {
      await router.push('/')
      return
    }
    await goAfterLogin()
  } catch (e) {
    error.value = e.message || 'Ошибка входа'
  }
}
</script>

<template>
  <div class="login-wrap">
    <div class="card login-card">
      <h1 class="page-title">AI Resume Screening</h1>
      <p class="page-sub">Система подбора и видео-собеседования</p>
      <p v-if="route.query.redirect && isInvitePath(route.query.redirect)" class="hint">
        Войдите с email и паролем из письма, затем откроется собеседование по вашей ссылке.
      </p>
      <p v-if="skipForm && !interviewChoices.length" class="hint">Вы уже вошли, переход…</p>
      <template v-if="!skipForm || interviewChoices.length">
        <form v-if="!interviewChoices.length" @submit.prevent="submit">
          <label>Email</label>
          <input v-model="email" type="email" required autocomplete="username" />
          <label>Пароль</label>
          <input v-model="password" type="password" required autocomplete="current-password" />
          <p v-if="error" class="error">{{ error }}</p>
          <button class="btn btn-primary" type="submit" style="width: 100%" :disabled="auth.loading">
            Войти
          </button>
        </form>
        <div v-if="interviewChoices.length" style="margin-top: 1.25rem">
          <p class="hint">Выберите собеседование:</p>
          <ul style="list-style: none; padding: 0; margin: 0.5rem 0 0">
            <li v-for="c in interviewChoices" :key="c.interview_id" style="margin-bottom: 0.5rem">
              <router-link :to="c.entry_path">Вакансия: {{ c.campaign_title }}</router-link>
            </li>
          </ul>
        </div>
      </template>
    </div>
  </div>
</template>
