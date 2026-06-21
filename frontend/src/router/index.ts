import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      name: 'create',
      component: () => import('@/views/CreateView.vue'),
      meta: { title: '创建试卷' },
    },
    {
      path: '/progress/:sessionId',
      name: 'progress',
      component: () => import('@/views/ProgressView.vue'),
      meta: { title: '生成进度' },
    },
    {
      path: '/preview/:sessionId',
      name: 'preview',
      component: () => import('@/views/PreviewView.vue'),
      meta: { title: '试卷预览' },
    },
    {
      path: '/textbook',
      name: 'textbook',
      component: () => import('@/views/TextbookView.vue'),
      meta: { title: '教材知识库' },
    },
    {
      path: '/questions',
      name: 'questions',
      component: () => import('@/views/QuestionUploadView.vue'),
      meta: { title: '历史题库' },
    },
  ],
})

export default router
