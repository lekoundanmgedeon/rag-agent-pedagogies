import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth.js'

const routes = [
  { path: '/login', name: 'login', component: () => import('@/views/LoginView.vue'), meta: { public: true } },

  // Espace élève (accessible aussi à l'admin).
  { path: '/', name: 'chat', component: () => import('@/views/ChatView.vue') },
  { path: '/c/:id', name: 'conversation', component: () => import('@/views/ChatView.vue') },
  { path: '/progression', name: 'progression', component: () => import('@/views/ProgressionView.vue') },

  // Espace administration (rôle admin requis).
  {
    path: '/admin',
    component: () => import('@/views/admin/AdminLayout.vue'),
    meta: { admin: true },
    children: [
      { path: '', name: 'admin-home', component: () => import('@/views/admin/DashboardView.vue') },
      { path: 'documents', name: 'admin-documents', component: () => import('@/views/admin/DocumentsView.vue') },
      { path: 'search', name: 'admin-search', component: () => import('@/views/admin/SearchView.vue') },
      { path: 'logs', name: 'admin-logs', component: () => import('@/views/admin/LogsView.vue') },
      { path: 'users', name: 'admin-users', component: () => import('@/views/admin/UsersView.vue') },
    ],
  },

  { path: '/:pathMatch(.*)*', redirect: '/' },
]

const router = createRouter({ history: createWebHistory(), routes })

router.beforeEach(async (to) => {
  const auth = useAuthStore()

  // Restaure la session (profil) au premier chargement si un jeton existe.
  if (auth.isAuthenticated && !auth.user) await auth.restore()

  if (to.meta.public) {
    return auth.isAuthenticated ? { name: 'chat' } : true
  }
  if (!auth.isAuthenticated) {
    return { name: 'login', query: { redirect: to.fullPath } }
  }
  if (to.meta.admin && !auth.isAdmin) {
    return { name: 'chat' }
  }
  return true
})

export default router
