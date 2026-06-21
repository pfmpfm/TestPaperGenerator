<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { getGenerationResult, getQuestion } from '@/api/generation'
import type { GenerationResultData, Question } from '@/api/types'
import MathText from '@/components/MathText.vue'

const route = useRoute()
const router = useRouter()
const sessionId = route.params.sessionId as string

const loading = ref(true)
const result = ref<GenerationResultData | null>(null)
const questions = ref<Question[]>([])
const showAnswers = ref(false)

// 按题型分组展示
const groupedQuestions = computed(() => {
  const groups: Record<string, Question[]> = {}
  for (const q of questions.value) {
    const t = q.question_type || '其他'
    if (!groups[t]) groups[t] = []
    groups[t].push(q)
  }
  return groups
})

async function loadData() {
  loading.value = true
  try {
    const res = await getGenerationResult(sessionId)
    if (!res.success || !res.data) return
    result.value = res.data

    // 并发拉取所有题目详情
    const ids = res.data.question_ids || []
    const results = await Promise.all(
      ids.map((id) => getQuestion(id).catch(() => null)),
    )
    questions.value = results
      .filter((r) => r && r.success && r.data)
      .map((r) => r!.data as Question)
  } finally {
    loading.value = false
  }
}

function handlePrint() {
  window.print()
}

onMounted(loadData)
</script>

<template>
  <div v-loading="loading">
    <!-- 工具栏(打印时隐藏) -->
    <div class="toolbar no-print">
      <el-button @click="router.push({ name: 'create' })">
        <el-icon><Back /></el-icon> 重新创建
      </el-button>
      <div class="toolbar-right">
        <el-switch
          v-model="showAnswers"
          active-text="显示答案"
          inactive-text="隐藏答案"
        />
        <el-button type="primary" @click="handlePrint">
          <el-icon><Printer /></el-icon> 打印 / 导出PDF
        </el-button>
      </div>
    </div>

    <!-- 试卷主体 -->
    <div v-if="result" class="paper">
      <h1 class="paper-title">{{ result.title }}</h1>
      <div class="paper-info">
        <span>年级: {{ result.metadata.grade }}</span>
        <span>科目: {{ result.metadata.subject }}</span>
        <span>时长: {{ result.metadata.duration_minutes }}分钟</span>
        <span>总分: {{ result.metadata.total_score }}分</span>
      </div>
      <div class="paper-meta-line">
        姓名: ____________ 班级: ____________ 学号: ____________
      </div>

      <div
        v-for="(group, type) in groupedQuestions"
        :key="type"
        class="question-group"
      >
        <h2 class="group-title">{{ type }} (共{{ group.length }}题)</h2>
        <div
          v-for="(q, idx) in group"
          :key="q.id"
          class="question-item"
        >
          <div class="question-content">
            <span class="question-no">{{ idx + 1 }}.</span>
            <MathText class="question-text" :text="q.content" />
          </div>
          <img
            v-if="q.figure_url"
            :src="q.figure_url"
            class="question-figure"
            alt="配图"
          />
          <div v-if="showAnswers" class="answer-block">
            <p class="answer-line">
              <strong>答案:</strong> <MathText :text="q.answer" />
            </p>
            <p v-if="q.explanation" class="answer-line">
              <strong>解析:</strong> <MathText :text="q.explanation" />
            </p>
          </div>
        </div>
      </div>

      <el-empty
        v-if="questions.length === 0 && !loading"
        description="暂无题目"
      />
    </div>
  </div>
</template>

<style scoped>
.toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}
.toolbar-right {
  display: flex;
  align-items: center;
  gap: 16px;
}
.paper {
  background: #fff;
  padding: 40px 48px;
  max-width: 800px;
  margin: 0 auto;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.08);
}
.paper-title {
  text-align: center;
  font-size: 24px;
  margin: 0 0 16px;
}
.paper-info {
  display: flex;
  justify-content: center;
  gap: 24px;
  color: #606266;
  font-size: 14px;
  margin-bottom: 12px;
}
.paper-meta-line {
  border-bottom: 1px solid #dcdfe6;
  padding-bottom: 16px;
  margin-bottom: 24px;
  color: #303133;
}
.group-title {
  font-size: 18px;
  border-left: 4px solid #409eff;
  padding-left: 10px;
  margin: 28px 0 16px;
}
.question-item {
  margin-bottom: 20px;
  line-height: 1.8;
}
.question-content {
  display: flex;
  gap: 6px;
}
.question-no {
  font-weight: 600;
}
.question-text {
  white-space: pre-wrap;
}
.question-figure {
  display: block;
  max-width: 280px;
  margin: 10px 0 10px 20px;
}
.answer-block {
  background: #f0f9eb;
  border-left: 3px solid #67c23a;
  padding: 8px 12px;
  margin: 8px 0 0 20px;
  border-radius: 4px;
}
.answer-line {
  margin: 4px 0;
  color: #303133;
}

/* 打印样式 */
@media print {
  .no-print {
    display: none !important;
  }
  .paper {
    box-shadow: none;
    max-width: 100%;
    padding: 0;
  }
  .answer-block {
    background: transparent;
  }
}
</style>
