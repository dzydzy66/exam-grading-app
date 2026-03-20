<template>
  <div class="upload-container">
    <el-card class="upload-card">
      <template #header>
        <div class="card-header">
          <span>选择考试</span>
        </div>
      </template>
      
      <el-form :model="form" :rules="rules" ref="formRef" label-width="100px">
        <el-form-item label="选择班级" prop="className">
          <el-select v-model="form.className" placeholder="请选择班级" style="width: 100%" @change="handleClassChange">
            <el-option 
              v-for="cls in classes" 
              :key="cls" 
              :label="cls" 
              :value="cls"
            />
          </el-select>
        </el-form-item>
        
        <el-form-item label="考试场次" prop="examId">
          <el-select v-model="form.examId" placeholder="请选择考试场次" style="width: 100%" :disabled="!form.className">
            <el-option 
              v-for="exam in filteredExams" 
              :key="exam.id" 
              :label="exam.name" 
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
    
    <!-- 标准答案管理 -->
    <el-card class="answer-card" v-if="form.examId">
      <template #header>
        <div class="card-header">
          <span>标准答案管理</span>
          <el-tag v-if="answerKeyData.updated_at" type="success">已更新: {{ answerKeyData.updated_at }}</el-tag>
          <el-tag v-else-if="answerKeyData.is_default" type="warning">使用默认答案</el-tag>
        </div>
      </template>
      
      <el-button type="primary" size="small" @click="showAnswerKeyDialog" style="margin-bottom: 15px;">
        <el-icon><Edit /></el-icon>
        编辑标准答案
      </el-button>
      
      <el-button type="warning" size="small" @click="handleRegrade" :loading="regrading" style="margin-bottom: 15px;">
        <el-icon><Refresh /></el-icon>
        重新批改所有试卷
      </el-button>
      
      <el-table :data="answerKeyData.answer_key?.questions || []" stripe max-height="400">
        <el-table-column prop="number" label="题号" width="60" />
        <el-table-column prop="type" label="题型" width="80" />
        <el-table-column prop="score" label="分值" width="60" />
        <el-table-column prop="correct_answer" label="标准答案" show-overflow-tooltip />
      </el-table>
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
    
    <!-- 编辑标准答案对话框 -->
    <el-dialog 
      v-model="showEditDialog" 
      title="编辑标准答案" 
      width="90%"
      top="5vh"
    >
      <div class="edit-answer-key">
        <el-form label-width="80px">
          <div v-for="(question, index) in editingAnswerKey.questions" :key="index" class="question-item">
            <el-row :gutter="20">
              <el-col :span="3">
                <el-form-item label="题号">
                  <el-input-number v-model="question.number" :min="1" size="small" />
                </el-form-item>
              </el-col>
              <el-col :span="4">
                <el-form-item label="题型">
                  <el-select v-model="question.type" size="small">
                    <el-option label="选择题" value="选择题" />
                    <el-option label="填空题" value="填空题" />
                    <el-option label="判断题" value="判断题" />
                    <el-option label="简答题" value="简答题" />
                    <el-option label="计算题" value="计算题" />
                    <el-option label="应用题" value="应用题" />
                  </el-select>
                </el-form-item>
              </el-col>
              <el-col :span="3">
                <el-form-item label="分值">
                  <el-input-number v-model="question.score" :min="1" size="small" />
                </el-form-item>
              </el-col>
            </el-row>
            <el-form-item label="题目">
              <el-input v-model="question.content" type="textarea" :rows="2" />
            </el-form-item>
            <el-form-item label="标准答案">
              <el-input v-model="question.correct_answer" type="textarea" :rows="2" />
            </el-form-item>
            <el-form-item label="解析">
              <el-input v-model="question.analysis" type="textarea" :rows="1" />
            </el-form-item>
            <el-divider />
          </div>
        </el-form>
        
        <div class="dialog-buttons">
          <el-button @click="addQuestion">添加题目</el-button>
          <el-button type="danger" @click="removeLastQuestion" v-if="editingAnswerKey.questions.length > 1">删除最后一题</el-button>
        </div>
      </div>
      
      <template #footer>
        <el-button @click="showEditDialog = false">取消</el-button>
        <el-button type="primary" @click="saveAnswerKey" :loading="saving">保存</el-button>
      </template>
    </el-dialog>
    
    <!-- 导航按钮 -->
    <div class="nav-buttons">
      <el-button @click="goToQuery">查看班级报告</el-button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, computed, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, type FormInstance } from 'element-plus'
import { getExams, getClasses, generateClassReport, getAnswerKey, updateAnswerKey, regradeExam } from '@/api'
import { useUserStore } from '@/stores/user'

interface Exam {
  id: number
  name: string
  class_name: string
}

interface Question {
  number: number
  type: string
  content: string
  correct_answer: string
  score: number
  analysis: string
}

interface AnswerKey {
  subject: string
  total_score: number
  questions: Question[]
}

const router = useRouter()
const userStore = useUserStore()
const formRef = ref<FormInstance>()
const loading = ref(false)
const regrading = ref(false)
const saving = ref(false)
const classes = ref<string[]>([])
const exams = ref<Exam[]>([])
const showProgressDialog = ref(false)
const showEditDialog = ref(false)

const form = reactive({
  className: '' as string,
  examId: null as number | null
})

const rules = {
  className: [
    { required: true, message: '请选择班级', trigger: 'change' }
  ],
  examId: [
    { required: true, message: '请选择考试场次', trigger: 'change' }
  ]
}

// 标准答案数据
const answerKeyData = ref<{
  exam_id?: number
  exam_name?: string
  answer_key?: AnswerKey
  updated_at?: string
  is_default?: boolean
}>({})

// 编辑中的标准答案
const editingAnswerKey = reactive<AnswerKey>({
  subject: '计算机组成与体系结构',
  total_score: 100,
  questions: []
})

// 过滤当前班级的考试
const filteredExams = computed(() => {
  if (!form.className) return []
  return exams.value.filter(e => e.class_name === form.className)
})

// 班级变化时清空考试选择
const handleClassChange = () => {
  form.examId = null
  answerKeyData.value = {}
}

// 监听考试选择变化
watch(() => form.examId, async (newVal) => {
  if (newVal) {
    await loadAnswerKey(newVal)
  } else {
    answerKeyData.value = {}
  }
})

// 加载标准答案
const loadAnswerKey = async (examId: number) => {
  try {
    const res: any = await getAnswerKey(examId)
    answerKeyData.value = res
  } catch (error) {
    ElMessage.error('加载标准答案失败')
  }
}

// 显示编辑标准答案对话框
const showAnswerKeyDialog = () => {
  if (answerKeyData.value.answer_key) {
    editingAnswerKey.subject = answerKeyData.value.answer_key.subject || '计算机组成与体系结构'
    editingAnswerKey.total_score = answerKeyData.value.answer_key.total_score || 100
    editingAnswerKey.questions = JSON.parse(JSON.stringify(answerKeyData.value.answer_key.questions))
  } else {
    editingAnswerKey.questions = [{
      number: 1,
      type: '选择题',
      content: '',
      correct_answer: '',
      score: 10,
      analysis: ''
    }]
  }
  showEditDialog.value = true
}

// 添加题目
const addQuestion = () => {
  editingAnswerKey.questions.push({
    number: editingAnswerKey.questions.length + 1,
    type: '选择题',
    content: '',
    correct_answer: '',
    score: 10,
    analysis: ''
  })
}

// 删除最后一题
const removeLastQuestion = () => {
  if (editingAnswerKey.questions.length > 1) {
    editingAnswerKey.questions.pop()
  }
}

// 保存标准答案
const saveAnswerKey = async () => {
  if (!form.examId) return
  
  saving.value = true
  try {
    // 计算总分
    editingAnswerKey.total_score = editingAnswerKey.questions.reduce((sum, q) => sum + q.score, 0)
    
    await updateAnswerKey(form.examId, editingAnswerKey)
    ElMessage.success('标准答案保存成功')
    showEditDialog.value = false
    await loadAnswerKey(form.examId)
  } catch (error) {
    ElMessage.error('保存失败')
  } finally {
    saving.value = false
  }
}

// 重新批改
const handleRegrade = async () => {
  if (!form.examId) return
  
  regrading.value = true
  try {
    const res: any = await regradeExam(form.examId)
    if (res.success) {
      ElMessage.success(res.message)
    } else {
      ElMessage.error(res.message)
    }
  } catch (error) {
    ElMessage.error('重新批改失败')
  } finally {
    regrading.value = false
  }
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
.upload-container {
  max-width: 900px;
  margin: 0 auto;
}

.upload-card, .answer-card {
  border-radius: 16px;
  margin-bottom: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
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

.edit-answer-key {
  max-height: 60vh;
  overflow-y: auto;
}

.question-item {
  padding: 10px;
  background: #f8f9fa;
  border-radius: 8px;
  margin-bottom: 15px;
}

.dialog-buttons {
  text-align: center;
  margin-top: 20px;
}
</style>
