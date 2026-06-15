import { createRouter, createWebHistory } from 'vue-router'
import { getToken } from '../api/client'
import { useAuthStore } from '../stores/auth'

const routes = [
  {
    path: '/i/:token',
    name: 'candidate-interview',
    component: () => import('../views/CandidateInterviewView.vue'),
    meta: { requiresAuth: true, role: 'candidate' },
  },
  { path: '/login', name: 'login', component: () => import('../views/LoginView.vue') },
  {
    path: '/',
    name: 'hr-campaigns',
    component: () => import('../views/HrCampaignsView.vue'),
    meta: { requiresAuth: true, role: 'hr' },
  },
  {
    path: '/campaigns/:id',
    name: 'hr-campaign-detail',
    component: () => import('../views/HrCampaignDetailView.vue'),
    meta: { requiresAuth: true, role: 'hr' },
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach(async (to) => {
  if (to.name === 'login') return true

  if (to.name === 'candidate-interview' && !getToken()) {
    return { name: 'login', query: { redirect: to.fullPath } }
  }

  if (!to.meta.requiresAuth) return true
  if (!getToken()) return { name: 'login' }

  const auth = useAuthStore()
  if (!auth.user) await auth.loadUser()
  if (!auth.user) {
    if (to.name === 'candidate-interview') {
      return { name: 'login', query: { redirect: to.fullPath } }
    }
    return { name: 'login' }
  }

  if (to.meta.role && auth.user.role !== to.meta.role) {
    if (auth.user.role === 'candidate') return { name: 'login' }
    return { name: 'hr-campaigns' }
  }
  return true
})

export default router
