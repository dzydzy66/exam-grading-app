import { ref, computed } from 'vue'
import type { Ref, ComputedRef } from 'vue'

interface UserInfo {
  id: number
  name: string
  role: 'student' | 'teacher'
  class_name?: string
}

// 用户信息
const user: Ref<UserInfo | null> = ref(null)

// 是否已登录
const isLoggedIn: ComputedRef<boolean> = computed(() => user.value !== null)

// 设置用户
const setUser = (userInfo: UserInfo | null) => {
  user.value = userInfo
  // 保存到 localStorage
  if (userInfo) {
    localStorage.setItem('user', JSON.stringify(userInfo))
  } else {
    localStorage.removeItem('user')
  }
}

// 获取用户
const getUser = (): UserInfo | null => {
  if (user.value) {
    return user.value
  }
  // 尝试从 localStorage 恢复
  const stored = localStorage.getItem('user')
  if (stored) {
    try {
      user.value = JSON.parse(stored)
      return user.value
    } catch {
      return null
    }
  }
  return null
}

// 清除用户
const clearUser = () => {
  user.value = null
  localStorage.removeItem('user')
}

export const useUserStore = () => {
  return {
    user,
    isLoggedIn,
    setUser,
    getUser,
    clearUser
  }
}
