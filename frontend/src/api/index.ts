import axios from 'axios'
import type { AxiosInstance } from 'axios'

const api: AxiosInstance = axios.create({
  baseURL: '/api',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json'
  }
})

// 请求拦截器
api.interceptors.request.use(
  (config) => {
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// 响应拦截器
api.interceptors.response.use(
  (response) => {
    return response.data
  },
  (error) => {
    return Promise.reject(error)
  }
)

// 登录接口
export const login = (account: string, role: string) => {
  return api.post('/login', { account, role })
}

// 学生登录
export const loginStudent = (account: string) => {
  return api.post('/login', { account, role: 'student' })
}

// 教师登录
export const loginTeacher = (account: string) => {
  return api.post('/login', { account, role: 'teacher' })
}

// 获取班级列表
export const getClasses = () => {
  return api.get('/classes')
}

// 获取考试类型列表
export const getExamTypes = () => {
  return api.get('/exam-types')
}

// 获取考试列表
export const getExams = (params?: { class_name?: string; teacher_id?: number }) => {
  return api.get('/exams', { params })
}

// 上传试卷
export const uploadExam = (formData: FormData) => {
  return api.post('/upload', formData, {
    headers: {
      'Content-Type': 'multipart/form-data'
    }
  })
}

// 查询上传状态
export const getUploadStatus = (uploadId: number) => {
  return api.get(`/upload-status/${uploadId}`)
}

// 查询学生成绩
export const getGrades = (studentId: number) => {
  return api.get('/grades', { params: { student_id: studentId } })
}

// 生成班级报告
export const generateClassReport = (examId: number) => {
  return api.post('/generate-class-report', { exam_id: examId })
}

// 获取标准答案
export const getAnswerKey = (examId: number) => {
  return api.get(`/answer-key/${examId}`)
}

// 更新标准答案
export const updateAnswerKey = (examId: number, answerKey: object) => {
  return api.post('/answer-key', { exam_id: examId, answer_key: answerKey })
}

// 重新批改
export const regradeExam = (examId: number) => {
  return api.post('/regrade', { exam_id: examId })
}

// 获取报告内容
export const getReportUrl = (fileName: string) => {
  return `/reports/${fileName}`
}

// 初始化测试数据
export const initData = () => {
  return api.post('/init-data')
}

export default api
