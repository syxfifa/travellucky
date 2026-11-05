import { createApp } from 'vue'
import { createRouter, createWebHistory } from 'vue-router'
import Antd from 'ant-design-vue'
import 'ant-design-vue/dist/reset.css'
import './styles/global.css'
import './styles/sunny-travel.css'
import App from './App.vue'
import { i18n } from './i18n'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      name: 'Landing',
      // 懒加载：结果页会带上 echarts / html2canvas / swiper / 地图 SDK。
      // 首页首屏不应该为这些结果页依赖付出加载成本。
      component: () => import('./views/Landing.vue')
    },
    {
      path: '/result',
      name: 'Result',
      component: () => import('./views/Result.vue')
    }
  ]
})

const app = createApp(App)

for (const [key, choices] of Object.entries({ theme: ['light', 'dark'], material: ['soft', 'clear', 'glass', 'gradient'], color: ['blue', 'mint', 'violet', 'sunset'], corner: ['tight', 'default', 'round'] })) {
  let saved: string | null = null
  try { saved = localStorage.getItem(`travellucky-${key}`) } catch {}
  document.documentElement.dataset[key] = saved && choices.includes(saved) ? saved : choices[0]
}

app.use(router)
app.use(Antd)
app.use(i18n)

app.mount('#app')


