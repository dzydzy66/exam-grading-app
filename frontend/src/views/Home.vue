<template>
  <div class="home-container">
    <div class="hero-section">
      <h1 class="hero-title">欢迎使用试卷批改系统</h1>
      <p class="hero-subtitle">智能批改，高效管理</p>
    </div>
    
    <div class="role-cards">
      <el-card class="role-card student-card" shadow="hover" @click="goToStudentLogin">
        <div class="card-content">
          <el-icon class="card-icon"><User /></el-icon>
          <h2>学生入口</h2>
          <p>上传试卷，查询成绩</p>
        </div>
      </el-card>
      
      <el-card class="role-card teacher-card" shadow="hover" @click="goToTeacherLogin">
        <div class="card-content">
          <el-icon class="card-icon"><Avatar /></el-icon>
          <h2>老师入口</h2>
          <p>生成班级报告，管理成绩</p>
        </div>
      </el-card>
    </div>
    
    <div class="test-accounts">
      <el-alert type="info" :closable="false">
        <template #title>
          <strong>测试账号</strong>
        </template>
        <p>学生账号：student001、student002、student003 等</p>
        <p>老师账号：teacher001、teacher002</p>
      </el-alert>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useRouter } from 'vue-router'

const router = useRouter()

const goToStudentLogin = () => {
  router.push('/student/login')
}

const goToTeacherLogin = () => {
  router.push('/teacher/login')
}
</script>

<style scoped>
.home-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: calc(100vh - 120px);
  padding: 40px;
}

.hero-section {
  text-align: center;
  margin-bottom: 60px;
}

.hero-title {
  font-size: 48px;
  font-weight: 700;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  margin-bottom: 16px;
}

.hero-subtitle {
  font-size: 20px;
  color: #666;
}

.role-cards {
  display: flex;
  gap: 40px;
  margin-bottom: 40px;
}

.role-card {
  width: 280px;
  cursor: pointer;
  border-radius: 16px;
  transition: all 0.3s ease;
  border: none;
}

.role-card:hover {
  transform: translateY(-8px);
}

.student-card {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}

.teacher-card {
  background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
}

.card-content {
  text-align: center;
  padding: 20px;
  color: white;
}

.card-icon {
  font-size: 48px;
  margin-bottom: 20px;
}

.card-content h2 {
  font-size: 24px;
  margin-bottom: 10px;
}

.card-content p {
  font-size: 14px;
  opacity: 0.9;
}

.test-accounts {
  width: 100%;
  max-width: 600px;
}

.test-accounts p {
  margin: 5px 0;
}
</style>
