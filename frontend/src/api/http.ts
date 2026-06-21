import axios, { type AxiosInstance, type AxiosResponse } from 'axios'
import { ElMessage } from 'element-plus'

// 后端统一响应格式
export interface ResponseBase<T = any> {
  success: boolean
  message: string
  data?: T
}

const http: AxiosInstance = axios.create({
  baseURL: '/api/v1',
  timeout: 300000, // 5分钟超时，支持大文档上传解析（PDF多页/LLM提取）
})

// 响应拦截：统一处理后端 ResponseBase 结构和错误
http.interceptors.response.use(
  (response: AxiosResponse<ResponseBase>) => response.data as any,
  (error) => {
    const msg =
      error.response?.data?.message ||
      error.response?.data?.detail ||
      error.message ||
      '请求失败'
    ElMessage.error(typeof msg === 'string' ? msg : '请求失败')
    return Promise.reject(error)
  },
)

export default http
