export type LectureStatus = 'ACTIVE' | 'PAUSED' | 'PROCESSING' | 'COMPLETED' | 'FAILED'

export type Category = {
  id: string
  name: string
}

export type LectureNode = {
  id: string
  parent_id: string | null
  label: string
  summary: string | null
}

export type LectureSegment = {
  id: string
  sequence: number
  transcript: string
  duration_seconds: number
  offset_seconds: number
  created_at: string
}

export type LectureSummary = {
  id: string
  user_id: string
  category: Category | null
  title: string | null
  status: LectureStatus
  duration_seconds: number
  nodes_count: number
  created_at: string
  updated_at: string
}

export type LectureDetail = {
  id: string
  user_id: string
  category: Category | null
  title: string | null
  status: LectureStatus
  duration_seconds: number
  summary: string | null
  nodes: LectureNode[]
  segments: LectureSegment[]
  created_at: string
  updated_at: string
}

export type ProcessSegmentResponse = {
  segment: LectureSegment
  insight_message: string | null
}

export type StartLecturePayload = {
  title?: string | null
  category_id?: string | null
}
