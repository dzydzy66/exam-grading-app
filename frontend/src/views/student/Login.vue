<template>
  <div class="login-container">
    <el-card class="login-card">
      <template #header>
        <div class="card-header">
          <span>学生登录</span>
        </div>
      </template>
      
      <el-form :model="form" :rules="rules" ref="formRef" label-width="80px">
        <el-form-item label="学号" prop="account">
          <el-input v-model="form.account" placeholder="请输入学号（如 S2201001）" />
        </el-form-item>
        
        <el-form-item>
          <el-button type="primary" @click="handleLogin" :loading="loading" style="width: 100%">
            登录
          </el-button>
        </el-form-item>
      </el-form>
      
      <div class="info-text">
        <el-alert title="本系统仅用于《计算机组成与体系结构》课程试卷评阅" type="info" :closable="false" show-icon />
      </div>
      
      <div class="test-accounts">
        <p>测试账号：</p>
        <ul>
          <li>S2201001 - 李明（计算机2201班）</li>
          <li>S2202001 - 刘洋（计算机2202班）</li>
          <li>S2203001 - 孙华（计算机2203班）</li>
        </ul>
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, type FormInstance } from 'element-plus'
import { loginStudent } from '@/api'
import { useUserStore } from '@/stores/user'

const router = useRouter()
const userStore = useUserStore()
const formRef = ref<FormInstance>()
const loading = ref(false)

const form = reactive({
  account: ''
})

const rules = {
  account: [
    { required: true, message: '请输入学号', trigger: 'blur' }
  ]
}

const handleLogin = async () => {
  if (!formRef.value) return
  
  await formRef.value.validate(async (valid) => {
    if (!valid) return
    
    loading.value = true
    try {
      const res: any = await loginStudent(form.account)
      
      if (res.success) {
        userStore.setUser({
          id: res.user_id,
          name: res.name,
          class_name: res.class_name,
          role: 'student'
        })
        ElMessage.success('登录成功')
        router.push('/student/upload')
      } else {
        ElMessage.error(res.message || '登录失败')
      }
    } catch (error) {
      ElMessage.error('登录失败，请稍后重试')
    } finally {
      loading.value = false
    }
  })
}
</script>

<style scoped>
.login-container {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 100vh;
  padding: 20px;
}

.login-card {
  width: 100%;
  max-width: 400px;
  border-radius: 16px;
}

.card-header {
  text-align: center;
  font-size: 20px;
  font-weight: 600;
}

.info-text {
  margin-top: 20px;
}

.test-accounts {
  margin-top: 15px;
  padding: 10px;
  background: #f5f7fa;
  border-radius: 8px;
  font-size: 12px;
  color: #666;
}

.test-accounts p {
  margin: 0 0 5px 0;
  font-weight: 600;
}

.test-accounts ul {
  margin: 0;
  padding-left: 20px;
}
</style>
