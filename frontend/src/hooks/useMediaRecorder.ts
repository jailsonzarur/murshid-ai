import { useCallback, useEffect, useRef } from 'react'

type Options = {
  chunkDurationMs: number
  onChunk: (blob: Blob, durationSeconds: number) => void
}

const CANDIDATE_MIME_TYPES = [
  'audio/webm;codecs=opus',
  'audio/webm',
  'audio/ogg;codecs=opus',
  'audio/mp4',
]

function pickMimeType() {
  if (typeof MediaRecorder === 'undefined') return ''
  return CANDIDATE_MIME_TYPES.find((type) => MediaRecorder.isTypeSupported(type)) ?? ''
}

export function useMediaRecorder({ chunkDurationMs, onChunk }: Options) {
  const recorderRef = useRef<MediaRecorder | null>(null)
  const streamRef = useRef<MediaStream | null>(null)
  const mimeTypeRef = useRef<string>('')
  const chunkStartedAtRef = useRef<number>(0)
  const cycleTimerRef = useRef<number | null>(null)
  const isPausedRef = useRef<boolean>(false)
  const stoppingForRestartRef = useRef<boolean>(false)
  const onChunkRef = useRef(onChunk)
  const buildRecorderRef = useRef<((stream: MediaStream) => MediaRecorder) | null>(null)
  const scheduleNextCycleRef = useRef<(() => void) | null>(null)

  useEffect(() => {
    onChunkRef.current = onChunk
  }, [onChunk])

  const clearCycleTimer = useCallback(() => {
    if (cycleTimerRef.current !== null) {
      window.clearTimeout(cycleTimerRef.current)
      cycleTimerRef.current = null
    }
  }, [])

  const cleanup = useCallback(() => {
    clearCycleTimer()
    recorderRef.current = null
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((track) => track.stop())
      streamRef.current = null
    }
  }, [clearCycleTimer])

  useEffect(() => {
    return () => {
      cleanup()
    }
  }, [cleanup])

  // build recorder + cycle scheduler via refs so they can call each other
  useEffect(() => {
    function scheduleNextCycle() {
      clearCycleTimer()
      cycleTimerRef.current = window.setTimeout(() => {
        const recorder = recorderRef.current
        if (!recorder || recorder.state !== 'recording') return
        stoppingForRestartRef.current = true
        recorder.stop()
      }, chunkDurationMs)
    }

    function buildRecorder(stream: MediaStream) {
      const mimeType = mimeTypeRef.current
      const collected: Blob[] = []

      const recorder = new MediaRecorder(stream, mimeType ? { mimeType } : undefined)

      recorder.ondataavailable = (event) => {
        if (event.data && event.data.size > 0) {
          collected.push(event.data)
        }
      }

      recorder.onstop = () => {
        const elapsedMs = chunkStartedAtRef.current
          ? performance.now() - chunkStartedAtRef.current
          : chunkDurationMs

        if (collected.length > 0) {
          const blob = new Blob(collected, { type: mimeType || collected[0].type || 'audio/webm' })
          onChunkRef.current(blob, elapsedMs / 1000)
        }

        if (stoppingForRestartRef.current) {
          stoppingForRestartRef.current = false
          if (streamRef.current && !isPausedRef.current && buildRecorderRef.current) {
            const next = buildRecorderRef.current(streamRef.current)
            recorderRef.current = next
            chunkStartedAtRef.current = performance.now()
            next.start()
            scheduleNextCycleRef.current?.()
          }
        }
      }

      return recorder
    }

    buildRecorderRef.current = buildRecorder
    scheduleNextCycleRef.current = scheduleNextCycle

    return () => {
      buildRecorderRef.current = null
      scheduleNextCycleRef.current = null
    }
  }, [chunkDurationMs, clearCycleTimer])

  const start = useCallback(async () => {
    if (!mimeTypeRef.current) {
      mimeTypeRef.current = pickMimeType()
    }

    const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
    streamRef.current = stream
    isPausedRef.current = false

    const recorder = buildRecorderRef.current?.(stream)
    if (!recorder) return
    recorderRef.current = recorder
    chunkStartedAtRef.current = performance.now()
    recorder.start()
    scheduleNextCycleRef.current?.()
  }, [])

  const pause = useCallback(() => {
    isPausedRef.current = true
    clearCycleTimer()
    const recorder = recorderRef.current
    if (recorder && recorder.state === 'recording') {
      stoppingForRestartRef.current = false
      recorder.stop()
    }
  }, [clearCycleTimer])

  const resume = useCallback(() => {
    if (!streamRef.current) return
    isPausedRef.current = false
    const recorder = buildRecorderRef.current?.(streamRef.current)
    if (!recorder) return
    recorderRef.current = recorder
    chunkStartedAtRef.current = performance.now()
    recorder.start()
    scheduleNextCycleRef.current?.()
  }, [])

  const stop = useCallback(() => {
    return new Promise<void>((resolve) => {
      clearCycleTimer()
      isPausedRef.current = false
      stoppingForRestartRef.current = false
      const recorder = recorderRef.current
      if (!recorder || recorder.state === 'inactive') {
        cleanup()
        resolve()
        return
      }
      recorder.addEventListener(
        'stop',
        () => {
          cleanup()
          resolve()
        },
        { once: true },
      )
      recorder.stop()
    })
  }, [cleanup, clearCycleTimer])

  return { start, pause, resume, stop }
}
