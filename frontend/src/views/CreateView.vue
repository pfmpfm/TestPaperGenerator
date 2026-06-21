<script setup lang="ts">
import { computed, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'
import { startGeneration } from '@/api/generation'
import type { ExamRequirement } from '@/api/types'

const router = useRouter()
const formRef = ref<FormInstance>()
const submitting = ref(false)

// 题型选项
const QUESTION_TYPES = ['选择题', '填空题', '应用题']

interface FormModel {
  grade: string
  subject: string
  knowledgePointsText: string
  questionTypes: Record<string, number>
  easy: number
  medium: number
  hard: number
}

const form = reactive<FormModel>({
  grade: '小学三年级',
  subject: '数学',
  knowledgePointsText: '两位数加减法\n乘法口诀',
  questionTypes: { 选择题: 5, 填空题: 3, 应用题: 2 },
  easy: 40,
  medium: 40,
  hard: 20,
})

const difficultyTotal = computed(() => form.easy + form.medium + form.hard)
const totalQuestions = computed(() =>
  Object.values(form.questionTypes).reduce((a, b) => a + b, 0),
)

const rules: FormRules = {
  grade: [{ required: true, message: '请输入年级', trigger: 'blur' }],
  subject: [{ required: true, message: '请输入科目', trigger: 'blur' }],
  knowledgePointsText: [
    { required: true, message: '请至少输入一个知识点', trigger: 'blur' },
  ],
}

async function handleSubmit() {
  if (!formRef.value) return
  await formRef.value.validate(async (valid) => {
    if (!valid) return

    if (difficultyTotal.value !== 100) {
      ElMessage.warning('难度分布之和必须为100%')
      return
    }
    if (totalQuestions.value <= 0) {
      ElMessage.warning('题目总数必须大于0')
      return
    }

    const knowledge_points = form.knowledgePointsText
      .split('\n')
      .map((s) => s.trim())
      .filter(Boolean)

    // 过滤数量为0的题型
    const question_types: Record<string, number> = {}
    for (const [k, v] of Object.entries(form.questionTypes)) {
      if (v > 0) question_types[k] = v
    }

    const requirement: ExamRequirement = {
      grade: form.grade,
      subject: form.subject,
      knowledge_points,
      question_types,
      difficulty_distribution: {
        简单: form.easy / 100,
        中等: form.medium / 100,
        困难: form.hard / 100,
      },
    }

    submitting.value = true
    try {
      const res = await startGeneration(requirement)
      if (res.success && res.data) {
        ElMessage.success('生成任务已启动')
        router.push({
          name: 'progress',
          params: { sessionId: res.data.session_id },
        })
      }
    } finally {
      submitting.value = false
    }
  })
}
</script>

<template>
  <el-card class="create-card">
    <template #header>
      <div class="card-header">
        <span>填写试卷需求</span>
        <div class="header-actions">
          <el-button size="small" @click="router.push('/questions')">
            📝 历史题库
          </el-button>
          <el-button size="small" @click="router.push('/textbook')">
            📚 教材知识库
          </el-button>
          <span class="hint">
            题目总数: {{ totalQuestions }} | 难度合计: {{ difficultyTotal }}%
          </span>
        </div>
      </div>
    </template>

    <el-form
      ref="formRef"
      :model="form"
      :rules="rules"
      label-width="120px"
      label-position="right"
    >
      <el-row :gutter="20">
        <el-col :span="12">
          <el-form-item label="年级" prop="grade">
            <el-select v-model="form.grade" placeholder="请选择年级">
              <el-option label="小学一年级" value="小学一年级" />
              <el-option label="小学二年级" value="小学二年级" />
              <el-option label="小学三年级" value="小学三年级" />
              <el-option label="小学四年级" value="小学四年级" />
              <el-option label="小学五年级" value="小学五年级" />
              <el-option label="小学六年级" value="小学六年级" />
              <el-option label="初中一年级" value="初中一年级" />
              <el-option label="初中二年级" value="初中二年级" />
              <el-option label="初中三年级" value="初中三年级" />
            </el-select>
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="科目" prop="subject">
            <el-select v-model="form.subject" placeholder="请选择科目">
              <el-option label="数学" value="数学" />
              <el-option label="语文" value="语文" />
              <el-option label="英语" value="英语" />
              <el-option label="物理" value="物理" />
              <el-option label="化学" value="化学" />
              <el-option label="生物" value="生物" />
            </el-select>
          </el-form-item>
        </el-col>
      </el-row>

      <el-form-item label="知识点" prop="knowledgePointsText">
        <el-input
          v-model="form.knowledgePointsText"
          type="textarea"
          :rows="4"
          placeholder="每行一个知识点"
        />
      </el-form-item>

      <el-form-item label="题型与数量">
        <div class="qtype-row">
          <div v-for="t in QUESTION_TYPES" :key="t" class="qtype-item">
            <span class="qtype-label">{{ t }}</span>
            <el-input-number
              v-model="form.questionTypes[t]"
              :min="0"
              :max="50"
              size="small"
            />
          </div>
        </div>
      </el-form-item>

      <el-form-item label="难度分布(%)">
        <div class="difficulty-row">
          <div class="difficulty-item">
            <span>简单</span>
            <el-input-number v-model="form.easy" :min="0" :max="100" size="small" />
          </div>
          <div class="difficulty-item">
            <span>中等</span>
            <el-input-number v-model="form.medium" :min="0" :max="100" size="small" />
          </div>
          <div class="difficulty-item">
            <span>困难</span>
            <el-input-number v-model="form.hard" :min="0" :max="100" size="small" />
          </div>
          <el-tag :type="difficultyTotal === 100 ? 'success' : 'danger'">
            合计 {{ difficultyTotal }}%
          </el-tag>
        </div>
      </el-form-item>

      <div style="text-align: center; margin-top: 32px;">
        <el-button
          type="primary"
          size="large"
          :loading="submitting"
          @click="handleSubmit"
        >
          开始生成试卷
        </el-button>
      </div>
    </el-form>
  </el-card>
</template>

<style scoped>
.create-card {
  max-width: 800px;
  margin: 0 auto;
}
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-weight: 600;
}
.header-actions {
  display: flex;
  gap: 12px;
  align-items: center;
}
.hint {
  font-size: 13px;
  color: #909399;
  font-weight: normal;
}
.qtype-row,
.difficulty-row {
  display: flex;
  gap: 24px;
  align-items: center;
  flex-wrap: wrap;
}
.qtype-item,
.difficulty-item {
  display: flex;
  align-items: center;
  gap: 8px;
}
.qtype-label {
  color: #606266;
}
</style>
