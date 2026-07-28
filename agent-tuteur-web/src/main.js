import { createApp } from 'vue'
import { createPinia } from 'pinia'
import 'katex/dist/katex.min.css' // styles des formules mathématiques
import App from './App.vue'
import router from './router/index.js'
import './composables/useTheme.js' // applique le thème au plus tôt

const app = createApp(App)
app.use(createPinia())
app.use(router)
app.mount('#app')
