import http, { type ResponseBase } from './http'

/**
 * 上传题目文档
 */
export function uploadQuestions(file: File, grade: string, subject: string): Promise<ResponseBase> {
  const formData = new FormData()
  formData.append('file', file)
  formData.append('grade', grade)
  formData.append('subject', subject)

  return http.post('/questions/upload', formData, {
    headers: {
      'Content-Type': 'multipart/form-data'
    }
  }) as Promise<ResponseBase>
}

/**
 * 上传题目文本（无需文件）
 */
export function uploadQuestionsText(text: string, grade: string, subject: string): Promise<ResponseBase> {
  const formData = new FormData()
  formData.append('text', text)
  formData.append('grade', grade)
  formData.append('subject', subject)

  return http.post('/questions/upload-text', formData, {
    headers: {
      'Content-Type': 'multipart/form-data'
    }
  }) as Promise<ResponseBase>
}

/**
 * 查询题目列表
 */
export function listQuestions(params: {
  grade?: string
  subject?: string
  difficulty?: string
  question_type?: string
  skip?: number
  limit?: number
}) {
  return http.get('/questions/', { params })
}

/**
 * 删除题目
 */
export function deleteQuestion(questionId: string) {
  return http.delete(`/questions/${questionId}`)
}
/**
 * 预览历史题库（RAG数据库）
 */
export function previewRagQuestions(params: {
  limit?: number
  offset?: number
  grade?: string
  subject?: string
}): Promise<ResponseBase> {
  return http.get('/questions/rag-preview', { params }) as Promise<ResponseBase>
}
