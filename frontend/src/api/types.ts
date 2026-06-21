// 与后端 schemas 对应的类型定义

export interface ExamRequirement {
  grade: string
  subject: string
  knowledge_points: string[]
  question_types: Record<string, number>
  difficulty_distribution: Record<string, number>
  duration_minutes?: number
  total_score?: number
}

export type SessionStatus = 'in_progress' | 'completed' | 'failed'

export interface ApiResponse<T = any> {
  success: boolean
  message: string
  data: T | null
}

export interface StartGenerationData {
  session_id: string
  status: SessionStatus
}

export interface GenerationStatusData {
  session_id: string
  status: SessionStatus
  workflow_state: Record<string, any> | null
  created_at: string
  updated_at: string
}

export interface PaperMetadata {
  grade: string
  subject: string
  duration_minutes: number
  total_score: number
  difficulty_distribution: Record<string, number>
  knowledge_points_covered: string[]
  question_count: number
}

export interface GenerationResultData {
  paper_id: string
  title: string
  metadata: PaperMetadata
  question_ids: string[]
  quality_score: number | null
  created_at: string
}

export interface Question {
  id: string
  content: string
  answer: string
  explanation: string | null
  question_type: string
  difficulty: string
  grade: string
  subject: string
  knowledge_points: string[]
  figure_url: string | null
  figure_spec: Record<string, any> | null
  quality_score: number | null
  is_approved: boolean
  created_at: string
  updated_at: string
}
