export interface Option {
  id: string
  text: string
  letter?: string
}

export interface Question {
  id: string
  type: 'OBJECTIVE_SINGLE' | 'OBJECTIVE_MULTI' | 'SUBJECTIVE'
  statement: string
  image_url?: string | null
  explanation?: string | null
  expected_answer?: string | null
  exam_order?: number
  options: Option[]
}

export type QuestionAnswer = string | string[] | Record<string, string>

export type ExamAnswers = Record<string, QuestionAnswer>

export type ResolutionMode = 'EXAM' | 'STUDY'
export type ResolutionStatus = 'IN_PROGRESS' | 'PAUSED' | 'SUBMITTED' | 'GRADED' | 'ERROR'
export type ResolutionResult = 'PASSED' | 'FAILED'
export type EvaluationSource = 'AUTO' | 'AI' | 'MANUAL'

export interface ResolutionSummary {
  id: string
  exam_id: string
  user_id: string
  mode: ResolutionMode
  status: ResolutionStatus
  result?: ResolutionResult | null
  score?: number | null
  started_at: string
  paused_at?: string | null
  submitted_at?: string | null
  graded_at?: string | null
  time_spent_seconds: number
  created_at: string
  updated_at: string
}

export interface QuestionResponseItem {
  id: string
  option_id?: string | null
  text_answer?: string | null
}

export interface QuestionResponseEvaluation {
  id: string
  score: number
  feedback?: string | null
  evaluation_source: EvaluationSource
  evaluated_at: string
  model_name?: string | null
}

export interface QuestionResponse {
  id: string
  question_id: string
  answered_at?: string | null
  items: QuestionResponseItem[]
  evaluation?: QuestionResponseEvaluation | null
}

export interface ResolutionQuestionDetail {
  question: Question
  response?: QuestionResponse | null
}

export interface ResolutionDetail {
  resolution: ResolutionSummary
  questions: ResolutionQuestionDetail[]
  can_show_evaluations: boolean
}

export interface ResolutionEvaluationTask {
  task_id: string
  resolution: ResolutionSummary
}
