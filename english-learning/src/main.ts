import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import router from './router'
import { applyTheme, getInitialTheme } from './stores/theme'
import './assets/main.css'

// 挂载前应用主题，避免闪屏（FOUC）
applyTheme(getInitialTheme())

const app = createApp(App)
app.use(createPinia())
app.use(router)
app.mount('#app')
