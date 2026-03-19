import { createRouter, createWebHistory } from 'vue-router'
import type { RouteRecordRaw } from 'vue-router'

const routes: RouteRecordRaw[] = [
  {
    path: '/',
    name: 'Home',
    component: () => import('@/views/Home.vue')
  },
  {
    path: '/student/login',
    name: 'StudentLogin',
    component: () => import('@/views/student/Login.vue')
  },
  {
    path: '/student/upload',
    name: 'StudentUpload',
    component: () => import('@/views/student/Upload.vue')
  },
  {
    path: '/student/query',
    name: 'StudentQuery',
    component: () => import('@/views/student/Query.vue')
  },
  {
    path: '/teacher/login',
    name: 'TeacherLogin',
    component: () => import('@/views/teacher/Login.vue')
  },
  {
    path: '/teacher/upload',
    name: 'TeacherUpload',
    component: () => import('@/views/teacher/Upload.vue')
  },
  {
    path: '/teacher/query',
    name: 'TeacherQuery',
    component: () => import('@/views/teacher/Query.vue')
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router
