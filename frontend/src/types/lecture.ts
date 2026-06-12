export type LectureStatus = 'ACTIVE' | 'PAUSED' | 'COMPLETED' | 'FAILED'

export type LectureEventType = 'TOPIC' | 'ALERT'

export type LectureEventSeverity = 'WARNING' | 'CRITICAL'

export type Category = {
  id: string
  name: string
}

export type LectureEvent = {
  id: string
  type: LectureEventType
  content: string
  severity: LectureEventSeverity | null
  sequence: number
  offset_seconds: number
  created_at: string
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
  topics_count: number
  alerts_count: number
  mindmap_markdown: string | null
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
  mindmap_markdown: string | null
  events: LectureEvent[]
  segments: LectureSegment[]
  created_at: string
  updated_at: string
}

export type ProcessSegmentResponse = {
  segment: LectureSegment
  new_events: LectureEvent[]
  mindmap_markdown: string | null
}

export type StartLecturePayload = {
  title?: string | null
  category_id?: string | null
}
