import { useCallback, useRef, useState } from 'react'

import { processLectureSegment } from '../lib/api'
import type { LectureEvent } from '../types/lecture'
import { useMediaRecorder } from './useMediaRecorder'

const CHUNK_DURATION_MS = 15_000

type Options = {
  lectureId: string
  initialEvents: LectureEvent[]
  initialMindmap: string | null
  onError?: (error: unknown) => void
}

type RecorderState = 'idle' | 'recording' | 'paused' | 'stopping'

export function useLectureRecorder({ lectureId, initialEvents, initialMindmap, onError }: Options) {
  const [state, setState] = useState<RecorderState>('idle')
  const [events, setEvents] = useState<LectureEvent[]>(initialEvents)
  const [mindmap, setMindmap] = useState<string | null>(initialMindmap)
  const [pendingChunks, setPendingChunks] = useState(0)

  const sequenceRef = useRef(0)
  const queueRef = useRef<Promise<void>>(Promise.resolve())

  const enqueueChunk = useCallback(
    (blob: Blob, durationSeconds: number) => {
      const sequence = ++sequenceRef.current
      setPendingChunks((count) => count + 1)
      queueRef.current = queueRef.current.then(async () => {
        try {
          const result = await processLectureSegment(lectureId, blob, sequence, durationSeconds)
          if (result.new_events.length > 0) {
            setEvents((prev) => [...prev, ...result.new_events])
          }
          if (result.mindmap_markdown) {
            setMindmap(result.mindmap_markdown)
          }
        } catch (error) {
          onError?.(error)
        } finally {
          setPendingChunks((count) => Math.max(0, count - 1))
        }
      })
    },
    [lectureId, onError],
  )

  const { start: startRecorder, pause: pauseRecorder, resume: resumeRecorder, stop: stopRecorder } =
    useMediaRecorder({
      chunkDurationMs: CHUNK_DURATION_MS,
      onChunk: enqueueChunk,
    })

  const start = useCallback(async () => {
    await startRecorder()
    setState('recording')
  }, [startRecorder])

  const pause = useCallback(() => {
    pauseRecorder()
    setState('paused')
  }, [pauseRecorder])

  const resume = useCallback(() => {
    resumeRecorder()
    setState('recording')
  }, [resumeRecorder])

  const stop = useCallback(async () => {
    setState('stopping')
    await stopRecorder()
    await queueRef.current
    setState('idle')
  }, [stopRecorder])

  return {
    state,
    events,
    mindmap,
    pendingChunks,
    isProcessing: pendingChunks > 0,
    start,
    pause,
    resume,
    stop,
  }
}
