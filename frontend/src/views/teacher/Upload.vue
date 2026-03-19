<template>
  <div class="upload-container">
    <el-card class="upload-card">
      <template #header>
        <div class="card-header">
          <span>选择考试</span>
        </div>
      </template>
      
      <el-form :model="form" :rules="rules" ref="formRef" label-width="100px">
        <el-form-item label="考试场次" prop="examId">
          <el-select v-model="form.examId" placeholder="请选择考试场次" style="width: 100%">
            <el-option 
              v-for="exam in exams" 
              :key="exam.id" 
              :label="`${exam.name} - ${exam.subject} (${exam.class_name})`" 
              :value="exam.id"
            />
          </el-select>
        </el-form-item>
        
        <el-form-item>
          <el-button type="primary" @click="handleGenerateReport" :loading="loading" style="width: 100%">
            生成班级报告
          </el-button>
        </el-form-item>
      </el-form>
    </el-card>
    
    <!-- 生成中提示 -->
    <el-dialog 
      v-model="showProgressDialog" 
      title="报告生成" 
      width="400px"
      :close-on-click-modal="false"
      :close-on-press-escape="false"
      :show-close="false"
    >
      <div class="progress-content">
        <el-icon class="loading-icon"><Loading /></el-icon>
        <p>正在生成报告，请稍后...</p>
      </div>
    </el-dialog>
    
    <!-- 导航按钮 -->
    <div class="nav-buttons">
      <el-button @click="goToQuery">查看班级报告</el-button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, type FormInstance } from 'element-plus'
import { getExams, generateClassReport } from '@/api'
import { useUserStore } from '@/stores/user'

interface Exam {
  id: number
  name: string
  subject: string
  class_name: string
}

const router = useRouter()
const userStore = useUserStore()
const formRef = ref<FormInstance>()
const loading = ref(false)
const exams = ref<Exam[]>([])
const showProgressDialog = ref(false)

const form = reactive({
  examId: null as number | null
})

const rules = {
  examId: [
    { required: true, message: '请选择考试场次', trigger: 'change' }
  ]
}

// 生成班级报告
const handleGenerateReport = async () => {
  if (!formRef.value) return
  
  await formRef.value.validate(async (valid) => {
    if (!valid) return
    
    const user = userStore.getUser()
    if (!user) {
      ElMessage.error('请先登录')
      router.push('/teacher/login')
      return
    }
    
    loading.value = true
    showProgressDialog.value = true
    
    try {
      const res: any = await generateClassReport(form.examId!)
      
      if (res.success) {
        ElMessage.success('班级报告生成成功！')
        showProgressDialog.value = false
        router.push('/teacher/query')
      } else {
        ElMessage.error(res.message || '生成失败')
        showProgressDialog.value = false
      }
    } catch (error) {
      ElMessage.error('生成失败，请稍后重试')
      showProgressDialog.value = false
    } finally {
      loading.value = false
    }
  })
}

// 跳转到报告查询
const goToQuery = () => {
  router.push('/teacher/query')
}

// 加载考试列表
onMounted(async () => {
  const user = userStore.getUser()
  if (!user) {
    router.push('/teacher/login')
    return
  }
  
  try {
    const res: any = await getExams({ teacher_id: user.id })
    exams.value = res
  } catch (error) {
    ElMessage.error('加载考试列表失败')
  }
})
</script>

<style scoped>
.upload-container {
  max-width: 600px;
  margin: 0 auto;
}

.upload-card {
  border-radius: 16px;
}

.card-header {
  font-size: 18px;
  font-weight: 600;
}

.progress-content {
  text-align: center;
  padding: 20px;
}

.loading-icon {
  font-size: 48px;
  color: #f5576c;
  animation: rotate 1s linear infinite;
}

@keyframes rotate {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.progress-content p {
  margin: 20px 0;
  color: #666;
}

.nav-buttons {
  text-align: center;
  margin-top: 20px;
}
</style>
