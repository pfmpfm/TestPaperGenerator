import http from './http'
import type {
  ApiResponse,
  ExamRequirement,
  GenerationResultData,
  GenerationStatusData,
  Question,
  StartGenerationData,
} from './types'

/** 启动试卷生成 */
export function startGeneration(requirement: ExamRequirement) {
  return http.post<any, ApiResponse<StartGenerationData>>(
    '/generation/start',
    requirement,
  )
}

/** 查询生成状态 */
export function getGenerationStatus(sessionId: string) {
  return http.get<any, ApiResponse<GenerationStatusData>>(
    `/generation/status/${sessionId}`,
  )
}

/** 获取生成结果(试卷) */
export function getGenerationResult(sessionId: string) {
  return http.get<any, ApiResponse<GenerationResultData>>(
    `/generation/result/${sessionId}`,
  )
}

/** 取消生成 */
export function cancelGeneration(sessionId: string) {
  return http.delete<any, ApiResponse<null>>(`/generation/cancel/${sessionId}`)
}

/** 获取单个题目详情 */
export function getQuestion(questionId: string) {
  return http.get<any, ApiResponse<Question>>(`/questions/${questionId}`)
}
