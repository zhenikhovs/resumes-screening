<script setup>
import { onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from './stores/auth'

const auth = useAuthStore()
const router = useRouter()

onMounted(async () => {
  await auth.loadUser()
})
</script>

<template>
  <header v-if="auth.user" class="nav">
    <span class="nav-brand">AI Resume Screening</span>
    <template v-if="auth.user.role === 'hr'">
      <router-link to="/">Подбор кандидатов</router-link>
    </template>
    <span style="margin-left: auto; font-size: 0.85rem; color: var(--muted)">{{ auth.user.email }}</span>
    <button
      class="btn btn-secondary"
      style="margin-left: 0.75rem; padding: 0.4rem 0.8rem"
      @click="auth.logout(); router.push('/login')"
    >
      Выйти
    </button>
  </header>
  <router-view />
</template>
