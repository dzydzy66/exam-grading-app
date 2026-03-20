<template>
  <div class="query-container">
    <el-card class="query-card">
      <template #header>
        <div class="card-header">
          <span>成绩查询 - {{ SUBJECT_NAME }}</span>
        </div>
      </template>
      
      <el-table :data="grades" stripe v-loading="loading" empty-text="暂无成绩记录">
        <el-table-column prop="exam_name" label="考试名称" width="150" />
        <el-table-column prop="subject" label="科目" width="180" />
        <el-table-column prop="score" label="得分" width="100">
          <template #default="{ row }">
            <el-tag :type="getScoreTagType(row.score)">{{ row.score }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="exam_date" label="考试日期" width="150" />
        <el-table-column label="操作" width="150">
          <template #default="{ row }">
            <el-button type="primary" size="small" @click="viewReport(row.report_file)">
              查看报告
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
    
    <!-- 报告对话框 -->
    <el-dialog 
      v-model="showReportDialog" 
      title="成绩报告" 
      width="80%"
      top="5vh"
      destroy-on-close
    >
      <div class="report-frame">
        <iframe :src="reportUrl" frameborder="0" width="100%" height="600px"></iframe>
      </div>
    </el-dialog>
    
    <!-- 导航按钮 -->
    <div class="nav-buttons">
      <el-button @click="goToUpload">上传试卷</el-button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { getGrades, getReportUrl } from '@/api'
import { useUserStore } from '@/stores/user'

const SUBJECT_NAME = '计算机组成与体系结构'

interface Grade {
  id: number
  exam_name: string
  subject: string
  score: number
  report_file: string
  exam_date: string
}

const router = useRouter()
const userStore = useUserStore()
const grades = ref<Grade[]>([])
const loading = ref(false)
const showReportDialog = ref(false)
const reportUrl = ref('')

// 获取分数标签类型
const getScoreTagType = (score: number): 'success' | 'warning' | 'danger' | 'info' => {
  if (score >= 90) return 'success'
  if (score >= 80) return 'info'
  if (score >= 60) return 'warning'
  return 'danger'
}

// 查看报告
const viewReport = (fileName: string) => {
  if (!fileName) {
    ElMessage.warning('报告文件不存在')
    return
  }
  reportUrl.value = getReportUrl(fileName)
  showReportDialog.value = true
}

// 跳转到上传页面
const goToUpload = () => {
  router.push('/student/upload')
}

// 加载成绩数据
onMounted(async () => {
  const user = userStore.getUser()
  if (!user) {
    router.push('/student/login')
    return
  }
  
  loading.value = true
  try {
    const res: any = await getGrades(user.id)
    grades.value = res
  } catch (error) {
    ElMessage.error('加载成绩失败')
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.query-container {
  max-width: 900px;
  margin: 0 auto;
}

.query-card {
  border-radius: 16px;
}

.card-header {
  font-size: 18px;
  font-weight: 600;
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
