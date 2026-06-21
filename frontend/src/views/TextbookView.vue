<template>
  <div class="textbook-upload-container">
    <el-card class="header-card">
      <h2>教材知识库管理</h2>
      <p class="subtitle">上传教材文档到知识库，支持 PDF、Word、PPT、Excel、HTML、TXT 等格式</p>
    </el-card>

    <!-- 上传表单 -->
    <el-card class="upload-card">
      <template #header>
        <span>上传教材文档</span>
      </template>

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

        <el-form-item label="章节">
          <el-input
            v-model="uploadForm.chapter"
            placeholder="选填，如：第三章 平行四边形"
            clearable
          />
        </el-form-item>

        <el-form-item label="文档文件" required>
          <el-upload
            ref="uploadRef"
            :auto-upload="false"
            :on-change="handleFileChange"
            :limit="1"
            :before-upload="beforeUpload"
            accept=".pdf,.docx,.doc,.pptx,.ppt,.xlsx,.xls,.html,.htm,.txt,.md"
          >
            <template #trigger>
              <el-button type="primary">选择文件</el-button>
            </template>
            <template #tip>
              <div class="el-upload__tip">
                支持格式：PDF、Word、PowerPoint、Excel、HTML、TXT、Markdown<br/>
                文件大小限制：10MB以内
              </div>
            </template>
          </el-upload>
        </el-form-item>

        <el-form-item>
          <el-button
            type="success"
            :loading="uploading"
            :disabled="!canUpload"
            @click="handleUpload"
          >
            {{ uploading ? '上传中...' : '上传到知识库' }}
          </el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 已上传文档列表 -->
    <el-card class="list-card">
      <template #header>
        <div class="card-header">
          <span>已上传文档</span>
          <el-button size="small" @click="loadFileList">刷新</el-button>
        </div>
      </template>

      <el-table :data="fileList" v-loading="loadingList">
        <el-table-column prop="name" label="文件名" min-width="200" />
        <el-table-column label="大小" width="120">
          <template #default="{ row }">
            {{ formatSize(row.size) }}
          </template>
        </el-table-column>
        <el-table-column label="上传时间" width="180">
          <template #default="{ row }">
            {{ formatTime(row.modified) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="100">
          <template #default="{ row }">
            <el-button
              type="danger"
              size="small"
              link
              @click="handleDelete(row.name)"
            >
              删除
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import type { UploadInstance, UploadRawFile } from 'element-plus'
import { uploadTextbook, listTextbooks, deleteTextbook } from '@/api/textbook'

const uploadForm = ref({
  grade: '',
  subject: '',
  chapter: ''
})

const uploadRef = ref<UploadInstance>()
const selectedFile = ref<UploadRawFile | null>(null)
const uploading = ref(false)
const loadingList = ref(false)
const fileList = ref<any[]>([])

const canUpload = computed(() => {
  return uploadForm.value.grade && uploadForm.value.subject && selectedFile.value
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

const handleUpload = async () => {
  if (!canUpload.value) {
    ElMessage.warning('请填写必填项并选择文件')
    return
  }

  uploading.value = true
  try {
    const res = await uploadTextbook(
      selectedFile.value!,
      uploadForm.value.grade,
      uploadForm.value.subject,
      uploadForm.value.chapter
    )

    if (res.success) {
      ElMessage.success(`上传成功！已索引 ${res.data.chunk_count} 个知识块`)
      // 清空表单
      uploadForm.value = { grade: '', subject: '', chapter: '' }
      selectedFile.value = null
      uploadRef.value?.clearFiles()
      // 刷新列表
      await loadFileList()
    } else {
      ElMessage.error(res.message || '上传失败')
    }
  } catch (error: any) {
    ElMessage.error(error.message || '上传失败')
  } finally {
    uploading.value = false
  }
}

const loadFileList = async () => {
  loadingList.value = true
  try {
    const res = await listTextbooks()
    if (res.success) {
      fileList.value = res.data || []
    }
  } catch (error) {
    console.error('加载文件列表失败:', error)
  } finally {
    loadingList.value = false
  }
}

const handleDelete = async (fileName: string) => {
  try {
    await ElMessageBox.confirm(`确定删除文档"${fileName}"吗？`, '删除确认', {
      type: 'warning'
    })

    const res = await deleteTextbook(fileName)
    if (res.success) {
      ElMessage.success('删除成功')
      await loadFileList()
    } else {
      ElMessage.error(res.message || '删除失败')
    }
  } catch (error: any) {
    if (error !== 'cancel') {
      ElMessage.error(error.message || '删除失败')
    }
  }
}

const formatSize = (bytes: number) => {
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
}

const formatTime = (timestamp: number) => {
  const date = new Date(timestamp * 1000)
  return date.toLocaleString('zh-CN')
}

onMounted(() => {
  loadFileList()
})
</script>

<style scoped>
.textbook-upload-container {
  padding: 20px;
  max-width: 1000px;
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
.list-card {
  margin-bottom: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.el-upload__tip {
  color: #909399;
  font-size: 12px;
  margin-top: 8px;
}
</style>