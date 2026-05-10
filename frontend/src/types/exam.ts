export interface Option {
  id: string
  text: string
  letter?: string
}

export interface Question {
  id: string
  type: 'OBJECTIVE' | 'SUBJECTIVE'
  statement: string
  image_url?: string | null
  options: Option[]
}

export type QuestionAnswer = string | Record<string, string>

export type ExamAnswers = Record<string, QuestionAnswer>
