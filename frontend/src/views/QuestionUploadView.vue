<template>
  <div class="question-upload-container">
    <el-card class="header-card">
      <h2>历史题库管理</h2>
      <p class="subtitle">上传优质题目到历史题库，LLM生成试卷时会参考这些题目</p>
    </el-card>

    <!-- 上传表单（支持文件和文本两种方式） -->
    <el-card class="upload-card">
      <el-tabs v-model="activeTab" type="border-card">
        <!-- 文件上传标签页 -->
        <el-tab-pane label="文件上传" name="file">
          <el-form :model="uploadForm" label-width="100px">
            <el-form-item label="年级" required>
              <el-select v-model="uploadForm.grade" placeholder="请选择年级">
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

            <el-form-item label="科目" required>
              <el-select v-model="uploadForm.subject" placeholder="请选择科目">
                <el-option label="数学" value="数学" />
                <el-option label="语文" value="语文" />
                <el-option label="英语" value="英语" />
                <el-option label="物理" value="物理" />
                <el-option label="化学" value="化学" />
                <el-option label="生物" value="生物" />
              </el-select>
            </el-form-item>

            <el-form-item label="题目文档" required>
              <el-upload
                ref="uploadRef"
                :auto-upload="false"
                :on-change="handleFileChange"
                :limit="1"
                :before-upload="beforeUpload"
                accept=".pdf,.docx,.doc,.txt,.md"
              >
                <template #trigger>
                  <el-button type="primary">选择文件</el-button>
                </template>
                <template #tip>
                  <div class="el-upload__tip">
                    支持格式：PDF、Word(docx/doc)、TXT、Markdown<br/>
                    文件大小限制：10MB以内<br/>
                    文档内容会用AI提取结构化题目（题干、答案、解析、题型、难度、知识点）
                  </div>
                </template>
              </el-upload>
            </el-form-item>

            <el-form-item>
              <el-button
                type="primary"
                :loading="uploading"
                :disabled="!canUploadFile"
                @click="handleFileUpload"
              >
                {{ uploading ? '上传中...' : '上传文档' }}
              </el-button>
            </el-form-item>
          </el-form>
        </el-tab-pane>

        <!-- 文本输入标签页 -->
        <el-tab-pane label="文本输入" name="text">
          <el-form :model="textForm" label-width="100px">
            <el-form-item label="年级" required>
              <el-select v-model="textForm.grade" placeholder="请选择年级">
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

            <el-form-item label="科目" required>
              <el-select v-model="textForm.subject" placeholder="请选择科目">
                <el-option label="数学" value="数学" />
                <el-option label="语文" value="语文" />
                <el-option label="英语" value="英语" />
                <el-option label="物理" value="物理" />
                <el-option label="化学" value="化学" />
                <el-option label="生物" value="生物" />
              </el-select>
            </el-form-item>

            <el-form-item label="题目内容" required>
              <el-input
                v-model="textForm.text"
                type="textarea"
                :rows="12"
                placeholder="请粘贴题目文本内容（至少50个字符）&#10;&#10;支持多道题目，每道题需包含：题干、答案、解析（可选）&#10;&#10;示例：&#10;1. 一个平行四边形的底是6厘米，高是4厘米，它的面积是多少？&#10;答案：24平方厘米&#10;解析：平行四边形面积=底×高=6×4=24平方厘米"
              />
              <div class="text-counter">
                {{ textForm.text.length }} / 50000 字符
              </div>
            </el-form-item>

            <el-form-item>
              <el-button
                type="primary"
                :loading="uploading"
                :disabled="!canUploadText"
                @click="handleTextUpload"
              >
                {{ uploading ? '上传中...' : '上传题目' }}
              </el-button>
            </el-form-item>
          </el-form>
        </el-tab-pane>
      </el-tabs>
    </el-card>

    <!-- 说明卡片 -->
    <el-card class="info-card">
      <template #header>
        <div style="display: flex; justify-content: space-between; align-items: center;">
          <span>💡 使用说明</span>
          <el-button type="primary" size="small" @click="showPreview">
            预览数据库
          </el-button>
        </div>
      </template>
      <ul>
        <li><strong>文件上传</strong>：上传PDF、Word等题目文档，AI自动提取结构化信息</li>
        <li><strong>文本输入</strong>：直接粘贴题目文本，适合快速添加少量题目</li>
        <li>上传的题目会存入历史题库，生成试卷时LLM会参考这些题目，提高生成质量</li>
        <li>建议题目格式规范，每道题包含：题干、答案、解析（可选）</li>
        <li>选择题需包含完整的A/B/C/D选项</li>
      </ul>
    </el-card>

    <!-- RAG预览对话框 -->
    <el-dialog
      v-model="previewVisible"
      title="历史题库预览（RAG数据库）"
      width="80%"
      :close-on-click-modal="false"
    >
      <el-form :inline="true" style="margin-bottom: 16px;">
        <el-form-item label="年级">
          <el-select v-model="previewFilter.grade" placeholder="全部" clearable style="width: 150px;">
            <el-option label="小学五年级" value="小学五年级" />
            <el-option label="小学六年级" value="小学六年级" />
            <el-option label="初中一年级" value="初中一年级" />
          </el-select>
        </el-form-item>
        <el-form-item label="科目">
          <el-select v-model="previewFilter.subject" placeholder="全部" clearable style="width: 120px;">
            <el-option label="数学" value="数学" />
            <el-option label="语文" value="语文" />
            <el-option label="英语" value="英语" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="loadPreviewData">查询</el-button>
        </el-form-item>
      </el-form>

      <el-table
        :data="previewData"
        v-loading="previewLoading"
        border
        style="width: 100%"
        max-height="500"
      >
        <el-table-column prop="content" label="题目内容" width="400" show-overflow-tooltip />
        <el-table-column prop="answer" label="答案" width="150" show-overflow-tooltip />
        <el-table-column prop="question_type" label="题型" width="100" />
        <el-table-column prop="difficulty" label="难度" width="100" />
        <el-table-column prop="grade" label="年级" width="120" />
        <el-table-column prop="subject" label="科目" width="100" />
        <el-table-column prop="knowledge_points" label="知识点" width="200">
          <template #default="{ row }">
            <el-tag
              v-for="(point, idx) in row.knowledge_points"
              :key="idx"
              size="small"
              style="margin-right: 4px;"
            >
              {{ point }}
            </el-tag>
          </template>
        </el-table-column>
      </el-table>

      <div style="margin-top: 16px; display: flex; justify-content: space-between; align-items: center;">
        <span>共 {{ previewTotal }} 条数据</span>
        <el-pagination
          v-model:current-page="previewPage"
          v-model:page-size="previewPageSize"
          :page-sizes="[10, 20, 50, 100]"
          :total="previewTotal"
          layout="total, sizes, prev, pager, next, jumper"
          @size-change="handlePreviewSizeChange"
          @current-change="handlePreviewPageChange"
        />
      </div>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { ElMessage } from 'element-plus'
import type { UploadInstance, UploadRawFile } from 'element-plus'
import { uploadQuestions, uploadQuestionsText, previewRagQuestions } from '@/api/questions'

const activeTab = ref('file')

// 文件上传表单
const uploadForm = ref({
  grade: '',
  subject: ''
})

// 文本上传表单
const textForm = ref({
  grade: '',
  subject: '',
  text: ''
})

// RAG预览
const previewVisible = ref(false)
const previewLoading = ref(false)
const previewData = ref<any[]>([])
const previewTotal = ref(0)
const previewPage = ref(1)
const previewPageSize = ref(20)
const previewFilter = ref({
  grade: '',
  subject: ''
})

const uploadRef = ref<UploadInstance>()
const selectedFile = ref<UploadRawFile | null>(null)
const uploading = ref(false)

const canUploadFile = computed(() => {
  return uploadForm.value.grade && uploadForm.value.subject && selectedFile.value
})

const canUploadText = computed(() => {
  return textForm.value.grade && textForm.value.subject && textForm.value.text.length >= 50
})

const handleFileChange = (file: any) => {
  selectedFile.value = file.raw
}

const beforeUpload = (file: File) => {
  const maxSize = 10 * 1024 * 1024 // 10MB
  if (file.size > maxSize) {
    ElMessage.error('文件大小不能超过 10MB，请选择较小的文档或分章节上传')
    return false
  }
  return true
}

const handleFileUpload = async () => {
  if (!canUploadFile.value) {
    ElMessage.warning('请填写必填项并选择文件')
    return
  }

  uploading.value = true
  try {
    const res = await uploadQuestions(
      selectedFile.value!,
      uploadForm.value.grade,
      uploadForm.value.subject
    )

    if (res.success) {
      ElMessage.success(res.message)
      // 清空表单
      uploadForm.value = { grade: '', subject: '' }
      selectedFile.value = null
      uploadRef.value?.clearFiles()
    } else {
      ElMessage.error(res.message || '上传失败')
    }
  } catch (error: any) {
    ElMessage.error(error.message || '上传失败')
  } finally {
    uploading.value = false
  }
}

const handleTextUpload = async () => {
  if (!canUploadText.value) {
    ElMessage.warning('请填写必填项，文本至少50个字符')
    return
  }

  uploading.value = true
  try {
    const res = await uploadQuestionsText(
      textForm.value.text,
      textForm.value.grade,
      textForm.value.subject
    )

    if (res.success) {
      ElMessage.success(res.message)
      // 清空表单
      textForm.value = { grade: '', subject: '', text: '' }
    } else {
      ElMessage.error(res.message || '上传失败')
    }
  } catch (error: any) {
    ElMessage.error(error.message || '上传失败')
  } finally {
    uploading.value = false
  }
}

const showPreview = () => {
  previewVisible.value = true
  previewPage.value = 1
  loadPreviewData()
}

const loadPreviewData = async () => {
  previewLoading.value = true
  try {
    const offset = (previewPage.value - 1) * previewPageSize.value
    const res = await previewRagQuestions({
      limit: previewPageSize.value,
      offset: offset,
      grade: previewFilter.value.grade || undefined,
      subject: previewFilter.value.subject || undefined,
    })

    if (res.success && res.data) {
      previewData.value = res.data.questions || []
      previewTotal.value = res.data.total || 0
    } else {
      ElMessage.error(res.message || '加载失败')
    }
  } catch (error: any) {
    ElMessage.error(error.message || '加载失败')
  } finally {
    previewLoading.value = false
  }
}

const handlePreviewPageChange = (page: number) => {
  previewPage.value = page
  loadPreviewData()
}

const handlePreviewSizeChange = (size: number) => {
  previewPageSize.value = size
  previewPage.value = 1
  loadPreviewData()
}
</script>

<style scoped>
.question-upload-container {
  padding: 20px;
  max-width: 800px;
  margin: 0 auto;
}

.header-card {
  margin-bottom: 20px;
}

.header-card h2 {
  margin: 0 0 8px 0;
  color: #303133;
}

.subtitle {
  margin: 0;
  color: #909399;
  font-size: 14px;
}

.upload-card,
.info-card {
  margin-bottom: 20px;
}

.el-upload__tip {
  color: #909399;
  font-size: 12px;
  margin-top: 8px;
  line-height: 1.6;
}

.info-card ul {
  margin: 0;
  padding-left: 20px;
}

.info-card li {
  margin-bottom: 8px;
  color: #606266;
  line-height: 1.6;
}

.text-counter {
  text-align: right;
  font-size: 12px;
  color: #909399;
  margin-top: 4px;
}
</style>