import http, { type ResponseBase } from './http'

/**
 * 上传教材文档
 */
export function uploadTextbook(file: File, grade: string, subject: string, chapter?: string): Promise<ResponseBase> {
  const formData = new FormData()
  formData.append('file', file)
  formData.append('grade', grade)
  formData.append('subject', subject)
  if (chapter) {
    formData.append('chapter', chapter)
  }

  return http.post('/textbook/upload', formData, {
    headers: {
      'Content-Type': 'multipart/form-data'
    }
  }) as Promise<ResponseBase>
}

/**
 * 检索教材知识
 */
export function searchTextbook(params: {
  query: string
  grade?: string
  subject?: string
  chapter?: string
  top_k?: number
}): Promise<ResponseBase> {
  const formData = new FormData()
  formData.append('query', params.query)
  if (params.grade) formData.append('grade', params.grade)
  if (params.subject) formData.append('subject', params.subject)
  if (params.chapter) formData.append('chapter', params.chapter)
  if (params.top_k) formData.append('top_k', params.top_k.toString())

  return http.post('/textbook/search', formData) as Promise<ResponseBase>
}

/**
 * 列出已上传文档
 */
export function listTextbooks(): Promise<ResponseBase> {
  return http.get('/textbook/list') as Promise<ResponseBase>
}

/**
 * 删除文档
 */
export function deleteTextbook(fileName: string): Promise<ResponseBase> {
  return http.delete(`/textbook/document/${fileName}`) as Promise<ResponseBase>
}

/**
 * 预览教材知识库（RAG数据库）
 */
export function previewRagChunks(params: {
  limit?: number
  offset?: number
  grade?: string
  subject?: string
}): Promise<ResponseBase> {
  return http.get('/textbook/rag-preview', { params }) as Promise<ResponseBase>
}