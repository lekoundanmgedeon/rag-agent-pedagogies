import { defineStore } from 'pinia'
import { authApi, getToken, setToken, clearToken, apiErrorMessage } from '@/services/api.js'

export const useAuthStore = defineStore('auth', {
  state: () => ({
    user: null,
    token: getToken(),
    loading: false,
    error: '',
  }),
  getters: {
    isAuthenticated: (s) => Boolean(s.token),
    isAdmin: (s) => s.user?.role === 'admin',
    isStudent: (s) => s.user?.role === 'student',
    displayName: (s) => s.user?.display_name || s.user?.email || '',
  },
  actions: {
    async login(email, password) {
      this.loading = true
      this.error = ''
      try {
        const { data } = await authApi.login(email, password)
        setToken(data.access_token)
        this.token = data.access_token
        this.user = data.user
        return true
      } catch (e) {
        this.error = apiErrorMessage(e, 'Identifiants invalides.')
        return false
      } finally {
        this.loading = false
      }
    },

    /** Restaure la session au chargement de l'app (jeton en localStorage). */
    async restore() {
      if (!this.token) return false
      try {
        const { data } = await authApi.me()
        this.user = data
        return true
      } catch {
        this.logout()
        return false
      }
    },

    logout() {
      clearToken()
      this.token = null
      this.user = null
    },
  },
})
