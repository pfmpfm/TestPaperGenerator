<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { cancelGeneration, getGenerationStatus } from '@/api/generation'
import type { SessionStatus } from '@/api/types'

const route = useRoute()
const router = useRouter()
const sessionId = route.params.sessionId as string

// workflow步骤定义(与后端节点对应)
const STEPS = [
  { key: 'parse_requirement', label: '解析需求' },
  { key: 'generate_questions', label: '生成题目' },
  { key: 'review_questions', label: '质量审核' },
  { key: 'assemble_paper', label: '组装试卷' },
  { key: 'completed', label: '完成' },
]

const status = ref<SessionStatus>('in_progress')
const currentStep = ref<string>('init')
const errorMsg = ref<string>('')
const questionCount = ref<number>(0)
let timer: number | undefined

// 当前步骤在进度条中的索引
const activeIndex = computed(() => {
  const idx = STEPS.findIndex((s) => s.key === currentStep.value)
  if (currentStep.value === 'completed') return STEPS.length
  return idx < 0 ? 0 : idx
})

const isFailed = computed(() => status.value === 'failed')
const isCompleted = computed(() => status.value === 'completed')

async function poll() {
  try {
    const res = await getGenerationStatus(sessionId)
    if (!res.success || !res.data) return

    status.value = res.data.status
    const state = res.data.workflow_state || {}
    currentStep.value = state.current_step || 'init'
    questionCount.value = state.question_count ?? 0

    if (status.value === 'completed') {
      stopPolling()
      setTimeout(() => {
        router.push({ name: 'preview', params: { sessionId } })
      }, 800)
    } else if (status.value === 'failed') {
      stopPolling()
      errorMsg.value = state.error || '生成失败'
    }
  } catch {
    // 错误已由拦截器提示，继续轮询
  }
}

function startPolling() {
  poll()
  timer = window.setInterval(poll, 2000)
}

function stopPolling() {
  if (timer) {
    clearInterval(timer)
    timer = undefined
  }
}

async function handleCancel() {
  stopPolling()
  try {
    await cancelGeneration(sessionId)
    ElMessage.info('已取消生成')
  } finally {
    router.push({ name: 'create' })
  }
}

onMounted(startPolling)
onBeforeUnmount(stopPolling)
</script>

<template>
  <el-card class="progress-card">
    <template #header>
      <span>试卷生成中</span>
    </template>

    <el-steps
      :active="activeIndex"
      align-center
      :process-status="isFailed ? 'error' : 'process'"
      :finish-status="'success'"
    >
      <el-step v-for="s in STEPS" :key="s.key" :title="s.label" />
    </el-steps>

    <div class="status-area">
      <template v-if="isCompleted">
        <el-result icon="success" title="生成完成！" sub-title="正在跳转到预览页...">
        </el-result>
      </template>

      <template v-else-if="isFailed">
        <el-result icon="error" title="生成失败" :sub-title="errorMsg">
          <template #extra>
            <el-button type="primary" @click="router.push({ name: 'create' })">
              返回重新创建
            </el-button>
          </template>
        </el-result>
      </template>

      <template v-else>
        <div class="loading-box">
          <el-icon class="is-loading rotating" :size="40"><Loading /></el-icon>
          <p class="loading-text">
            正在处理:
            {{ STEPS.find((s) => s.key === currentStep)?.label || '准备中' }}
          </p>
          <p v-if="questionCount > 0" class="sub-text">
            已生成 {{ questionCount }} 道题
          </p>
          <el-button @click="handleCancel">取消生成</el-button>
        </div>
      </template>
    </div>
  </el-card>
</template>

<style scoped>
.progress-card {
  max-width: 800px;
  margin: 0 auto;
}
.status-area {
  margin-top: 40px;
  min-height: 200px;
  display: flex;
  align-items: center;
  justify-content: center;
}
.loading-box {
  text-align: center;
}
.rotating {
  animation: rotate 1.5s linear infinite;
  color: #409eff;
}
@keyframes rotate {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}
.loading-text {
  font-size: 16px;
  color: #303133;
  margin: 16px 0 8px;
}
.sub-text {
  color: #909399;
  margin-bottom: 16px;
}
</style>
