<template>
  <div class="query-container">
    <el-card class="query-card">
      <template #header>
        <div class="card-header">
          <span>班级报告</span>
        </div>
      </template>
      
      <el-form :inline="true" class="search-form">
        <el-form-item label="选择班级">
          <el-select v-model="selectedClassName" placeholder="请选择班级" @change="handleClassChange">
            <el-option 
              v-for="cls in classes" 
              :key="cls" 
              :label="cls" 
              :value="cls"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="考试场次">
          <el-select v-model="selectedExamId" placeholder="请选择考试场次" :disabled="!selectedClassName">
            <el-option 
              v-for="exam in filteredExams" 
              :key="exam.id" 
              :label="exam.name" 
              :value="exam.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="viewReport" :disabled="!selectedExamId">
            查看报告
          </el-button>
        </el-form-item>
      </el-form>
    </el-card>
    
    <!-- 报告展示 -->
    <el-card class="report-card" v-if="reportUrl">
      <div class="report-frame">
        <iframe :src="reportUrl" frameborder="0" width="100%" height="600px"></iframe>
      </div>
    </el-card>
    
    <!-- 导航按钮 -->
    <div class="nav-buttons">
      <el-button @click="goToUpload">生成报告</el-button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { getExams, getClasses, getReportUrl } from '@/api'
import { useUserStore } from '@/stores/user'

interface Exam {
  id: number
  name: string
  class_name: string
}

const router = useRouter()
const userStore = useUserStore()
const classes = ref<string[]>([])
const exams = ref<Exam[]>([])
const selectedClassName = ref<string>('')
const selectedExamId = ref<number | null>(null)
const reportUrl = ref('')

// 过滤当前班级的考试
const filteredExams = computed(() => {
  if (!selectedClassName.value) return []
  return exams.value.filter(e => e.class_name === selectedClassName.value)
})

// 班级变化处理
const handleClassChange = () => {
  selectedExamId.value = null
  reportUrl.value = ''
}

// 查看报告
const viewReport = () => {
  if (!selectedExamId.value) {
    ElMessage.warning('请选择考试场次')
    return
  }
  
  const fileName = `class_exam_${selectedExamId.value}.html`
  reportUrl.value = getReportUrl(fileName)
}

// 跳转到上传页面
const goToUpload = () => {
  router.push('/teacher/upload')
}

// 加载数据
onMounted(async () => {
  const user = userStore.getUser()
  if (!user) {
    router.push('/teacher/login')
    return
  }
  
  try {
    // 加载班级列表
    const classRes: any = await getClasses()
    classes.value = classRes.classes || []
    
    // 加载考试列表
    const examRes: any = await getExams({ teacher_id: user.id })
    exams.value = examRes
  } catch (error) {
    ElMessage.error('加载数据失败')
  }
})
</script>

<style scoped>
.query-container {
  max-width: 1200px;
  margin: 0 auto;
}

.query-card {
  border-radius: 16px;
  margin-bottom: 20px;
}

.card-header {
  font-size: 18px;
  font-weight: 600;
}

.search-form {
  margin-bottom: 0;
}

.report-card {
  border-radius: 16px;
}

.report-frame {
  background: #f5f7fa;
  border-radius: 8px;
  overflow: hidden;
}

.nav-buttons {
  text-align: center;
  margin-top: 20px;
}
</style>
