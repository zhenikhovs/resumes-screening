import { defineStore } from 'pinia'
import { ref } from 'vue'
import { clearToken, fetchMe, getToken, login as apiLogin } from '../api/client'

export const useAuthStore = defineStore('auth', () => {
  const user = ref(null)
  const loading = ref(false)

  async function login(email, password) {
    loading.value = true
    try {
      await apiLogin(email, password)
      user.value = await fetchMe()
      return user.value
    } finally {
      loading.value = false
    }
  }

  async function loadUser() {
    if (!getToken()) return null
    try {
      user.value = await fetchMe()
      return user.value
    } catch {
      clearToken()
      user.value = null
      return null
    }
  }

  function logout() {
    clearToken()
    user.value = null
  }

  return { user, loading, login, loadUser, logout }
})
