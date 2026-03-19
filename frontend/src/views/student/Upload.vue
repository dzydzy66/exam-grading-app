<template>
  <div class="upload-container">
    <el-card class="upload-card">
      <template #header>
        <div class="card-header">
          <span>上传试卷</span>
        </div>
      </template>
      
      <el-form :model="form" :rules="rules" ref="formRef" label-width="100px">
        <el-form-item label="考试场次" prop="examId">
          <el-select v-model="form.examId" placeholder="请选择考试场次" style="width: 100%">
            <el-option 
              v-for="exam in exams" 
              :key="exam.id" 
              :label="`${exam.name} - ${exam.subject}`" 
              :value="exam.id"
            />
          </el-select>
        </el-form-item>
        
        <el-form-item label="试卷图片" prop="image">
          <el-upload
            :auto-upload="false"
            :limit="1"
            :on-change="handleFileChange"
            :on-exceed="handleExceed"
            accept="image/*"
            drag
          >
            <el-icon class="el-icon--upload"><Upload /></el-icon>
            <div class="el-upload__text">
              将试卷图片拖到此处，或<em>点击上传</em>
            </div>
            <template #tip>
              <div class="el-upload__tip">
                支持 jpg、png 格式图片
              </div>
            </template>
          </el-upload>
        </el-form-item>
        
        <el-form-item>
          <el-button type="primary" @click="handleSubmit" :loading="loading" style="width: 100%">
            提交试卷
          </el-button>
        </el-form-item>
      </el-form>
    </el-card>
    
    <!-- 批改中提示 -->
    <el-dialog 
      v-model="showProgressDialog" 
      title="批改进度" 
      width="400px"
      :close-on-click-modal="false"
      :close-on-press-escape="false"
      :show-close="false"
    >
      <div class="progress-content">
        <el-icon class="loading-icon"><Loading /></el-icon>
        <p>批改中，请稍后...</p>
        <el-progress :percentage="progress" :status="progressStatus" />
      </div>
    </el-dialog>
    
    <!-- 导航按钮 -->
    <div class="nav-buttons">
      <el-button @click="goToQuery">查看成绩</el-button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, type FormInstance, type UploadProps } from 'element-plus'
import { getExams, uploadExam, getUploadStatus } from '@/api'
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
const progress = ref(0)
const progressStatus = ref<'' | 'success' | 'warning' | 'exception'>('')

const form = reactive({
  examId: null as number | null,
  image: null as File | null
})

const rules = {
  examId: [
    { required: true, message: '请选择考试场次', trigger: 'change' }
  ],
  image: [
    { required: true, message: '请上传试卷图片', trigger: 'change' }
  ]
}

// 文件变化处理
const handleFileChange: UploadProps['onChange'] = (uploadFile) => {
  form.image = uploadFile.raw || null
}

// 超出限制处理
const handleExceed: UploadProps['onExceed'] = () => {
  ElMessage.warning('只能上传一个文件')
}

// 提交试卷
const handleSubmit = async () => {
  if (!formRef.value) return
  
  await formRef.value.validate(async (valid) => {
    if (!valid) return
    
    if (!form.image) {
      ElMessage.error('请上传试卷图片')
      return
    }
    
    const user = userStore.getUser()
    if (!user) {
      ElMessage.error('请先登录')
      router.push('/student/login')
      return
    }
    
    loading.value = true
    showProgressDialog.value = true
    progress.value = 0
    progressStatus.value = ''
    
    try {
      const formData = new FormData()
      formData.append('student_id', user.id.toString())
      formData.append('exam_id', form.examId!.toString())
      formData.append('image', form.image)
      
      const res: any = await uploadExam(formData)
      
      if (res.success) {
        progress.value = 30
        ElMessage.success(res.message)
        
        // 轮询检查批改状态
        await checkGradingStatus(res.upload_id)
      } else {
        progressStatus.value = 'exception'
        ElMessage.error(res.message || '上传失败')
      }
    } catch (error) {
      progressStatus.value = 'exception'
      ElMessage.error('上传失败，请稍后重试')
    } finally {
      loading.value = false
    }
  })
}

// 检查批改状态
const checkGradingStatus = async (uploadId: number) => {
  const maxAttempts = 30 // 最多检查30次
  let attempts = 0
  
  const check = async (): Promise<void> => {
    attempts++
    
    try {
      const res: any = await getUploadStatus(uploadId)
      
      if (res.status === 'completed') {
        progress.value = 100
        progressStatus.value = 'success'
        ElMessage.success('批改完成！')
        setTimeout(() => {
          showProgressDialog.value = false
          router.push('/student/query')
        }, 1500)
        return
      }
      
      if (res.status === 'failed') {
        progressStatus.value = 'exception'
        ElMessage.error('批改失败，请稍后重试')
        return
      }
      
      // 继续等待
      if (attempts < maxAttempts) {
        progress.value = Math.min(30 + attempts * 2, 90)
        await new Promise(resolve => setTimeout(resolve, 2000))
        await check()
      } else {
        progressStatus.value = 'warning'
        ElMessage.warning('批改超时，请稍后查看成绩')
      }
    } catch (error) {
      progressStatus.value = 'exception'
      ElMessage.error('查询状态失败')
    }
  }
  
  await check()
}

// 跳转到成绩查询
const goToQuery = () => {
  router.push('/student/query')
}

// 加载考试列表
onMounted(async () => {
  const user = userStore.getUser()
  if (!user) {
    router.push('/student/login')
    return
  }
  
  try {
    const res: any = await getExams()
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
  color: #667eea;
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
