import { useEffect, useMemo, useRef, useState } from 'react'
import {
  Background,
  Controls,
  Handle,
  Position,
  ReactFlow,
  ReactFlowProvider,
  useEdgesState,
  useNodesState,
  useReactFlow,
  type Edge,
  type Node as RFNode,
  type NodeProps,
} from '@xyflow/react'
import dagre from 'dagre'

import '@xyflow/react/dist/style.css'

import type { LectureNode } from '../../types/lecture'
import { Icon } from '../ui/icon'

const NODE_WIDTH = 260
const NODE_HEIGHT = 96
const PULSE_DURATION_MS = 1200
const FADE_DURATION_MS = 400

type NodeData = {
  label: string
  summary: string | null
  isFresh: boolean
  isFading: boolean
  isRoot: boolean
  [key: string]: unknown
}

type TopicRFNode = RFNode<NodeData>

function buildLayout(
  lectureNodes: LectureNode[],
  freshIds: Set<string>,
  fadingIds: Set<string>,
) {
  if (lectureNodes.length === 0) {
    return { nodes: [] as TopicRFNode[], edges: [] as Edge[] }
  }

  const dagreGraph = new dagre.graphlib.Graph()
  dagreGraph.setDefaultEdgeLabel(() => ({}))
  dagreGraph.setGraph({ rankdir: 'TB', nodesep: 40, ranksep: 70, marginx: 24, marginy: 24 })

  const validIds = new Set(lectureNodes.map((node) => node.id))

  lectureNodes.forEach((node) => {
    dagreGraph.setNode(node.id, { width: NODE_WIDTH, height: NODE_HEIGHT })
  })

  const edges: Edge[] = []
  lectureNodes.forEach((node) => {
    if (node.parent_id && validIds.has(node.parent_id)) {
      dagreGraph.setEdge(node.parent_id, node.id)
      const fading = fadingIds.has(node.id) || fadingIds.has(node.parent_id)
      edges.push({
        id: `e-${node.parent_id}-${node.id}`,
        source: node.parent_id,
        target: node.id,
        type: 'smoothstep',
        animated: false,
        style: {
          stroke: 'oklch(72% 0.04 270)',
          strokeWidth: 1.4,
          opacity: fading ? 0 : 1,
          transition: `opacity ${FADE_DURATION_MS}ms ease-out`,
        },
      })
    }
  })

  dagre.layout(dagreGraph)

  const nodes: TopicRFNode[] = lectureNodes.map((node) => {
    const pos = dagreGraph.node(node.id)
    return {
      id: node.id,
      type: 'topic',
      position: { x: pos.x - NODE_WIDTH / 2, y: pos.y - NODE_HEIGHT / 2 },
      data: {
        label: node.label,
        summary: node.summary,
        isFresh: freshIds.has(node.id),
        isFading: fadingIds.has(node.id),
        isRoot: node.parent_id === null,
      },
    }
  })

  return { nodes, edges }
}

function TopicNode({ data }: NodeProps<TopicRFNode>) {
  const { label, summary, isFresh, isFading, isRoot } = data

  return (
    <div
      style={{
        width: NODE_WIDTH,
        minHeight: NODE_HEIGHT,
        padding: '12px 14px',
        borderRadius: 12,
        background: isRoot ? 'oklch(58% 0.18 285)' : '#fff',
        color: isRoot ? '#fff' : 'var(--ink)',
        border: isRoot ? 'none' : '1px solid var(--line)',
        boxShadow: isFresh
          ? '0 0 0 3px oklch(82% 0.16 140 / 0.6), 0 4px 12px rgba(0,0,0,0.08)'
          : '0 1px 3px rgba(0,0,0,0.05)',
        transition: `box-shadow 0.3s ease, opacity ${FADE_DURATION_MS}ms ease-out, transform ${FADE_DURATION_MS}ms ease-out`,
        animation: isFresh ? 'tree-node-pulse 1.2s ease-out' : undefined,
        opacity: isFading ? 0 : 1,
        transform: isFading ? 'scale(0.9)' : 'scale(1)',
        pointerEvents: isFading ? 'none' : 'auto',
        fontFamily: 'var(--sans)',
      }}
    >
      <Handle type="target" position={Position.Top} style={{ opacity: 0, pointerEvents: 'none' }} />
      <div
        style={{
          fontSize: 13.5,
          fontWeight: 700,
          letterSpacing: '-0.01em',
          lineHeight: 1.3,
          marginBottom: summary ? 4 : 0,
        }}
      >
        {label}
      </div>
      {summary ? (
        <div
          style={{
            fontSize: 11.5,
            color: isRoot ? 'rgba(255,255,255,0.85)' : 'var(--ink-3)',
            lineHeight: 1.4,
            display: '-webkit-box',
            WebkitLineClamp: 3,
            WebkitBoxOrient: 'vertical',
            overflow: 'hidden',
          }}
          title={summary}
        >
          {summary}
        </div>
      ) : null}
      <Handle type="source" position={Position.Bottom} style={{ opacity: 0, pointerEvents: 'none' }} />
    </div>
  )
}

const nodeTypes = { topic: TopicNode }

type TreeViewerInnerProps = {
  lectureNodes: LectureNode[]
  isProcessing: boolean
  isFullscreen: boolean
  onToggleFullscreen: () => void
}

function TreeViewerInner({
  lectureNodes,
  isProcessing,
  isFullscreen,
  onToggleFullscreen,
}: TreeViewerInnerProps) {
  const [displayedNodes, setDisplayedNodes] = useState<LectureNode[]>(lectureNodes)
  const [freshIds, setFreshIds] = useState<Set<string>>(new Set())
  const [fadingIds, setFadingIds] = useState<Set<string>>(new Set())
  const lastSnapshotsRef = useRef<Map<string, LectureNode>>(
    new Map(lectureNodes.map((node) => [node.id, node])),
  )
  const { fitView } = useReactFlow()

  // sync displayedNodes from prop, detect additions/removals/updates
  useEffect(() => {
    const incomingIds = new Set(lectureNodes.map((node) => node.id))
    const previousIds = new Set(lastSnapshotsRef.current.keys())

    const justAdded: string[] = []
    incomingIds.forEach((id) => {
      if (!previousIds.has(id)) justAdded.push(id)
    })

    const justRemoved: string[] = []
    previousIds.forEach((id) => {
      if (!incomingIds.has(id)) justRemoved.push(id)
    })

    // snapshots for nodes that disappeared (so we can keep them visible while fading)
    const removedSnapshots = justRemoved
      .map((id) => lastSnapshotsRef.current.get(id))
      .filter((node): node is LectureNode => node !== undefined)

    // updated snapshot map for next diff
    lastSnapshotsRef.current = new Map(lectureNodes.map((node) => [node.id, node]))

    // pulse animation on new nodes
    if (justAdded.length > 0) {
      setFreshIds((prev) => {
        const next = new Set(prev)
        justAdded.forEach((id) => next.add(id))
        return next
      })
      window.setTimeout(() => {
        setFreshIds((prev) => {
          const next = new Set(prev)
          justAdded.forEach((id) => next.delete(id))
          return next
        })
      }, PULSE_DURATION_MS)
    }

    // start fade on removed nodes — keep them in displayedNodes until fade completes
    if (justRemoved.length > 0) {
      setFadingIds((prev) => {
        const next = new Set(prev)
        justRemoved.forEach((id) => next.add(id))
        return next
      })

      // merged display: incoming nodes (with fresh data) + soon-to-fade snapshots
      setDisplayedNodes([...lectureNodes, ...removedSnapshots])

      window.setTimeout(() => {
        setFadingIds((prev) => {
          const next = new Set(prev)
          justRemoved.forEach((id) => next.delete(id))
          return next
        })
        setDisplayedNodes((current) => current.filter((node) => !justRemoved.includes(node.id)))
      }, FADE_DURATION_MS)
    } else {
      setDisplayedNodes(lectureNodes)
    }
  }, [lectureNodes])

  const layout = useMemo(
    () => buildLayout(displayedNodes, freshIds, fadingIds),
    [displayedNodes, freshIds, fadingIds],
  )

  const [nodes, setNodes, onNodesChange] = useNodesState<TopicRFNode>(layout.nodes)
  const [edges, setEdges, onEdgesChange] = useEdgesState<Edge>(layout.edges)

  useEffect(() => {
    setNodes(layout.nodes)
    setEdges(layout.edges)
    // refit on structure change
    const id = window.setTimeout(() => {
      void fitView({ padding: 0.2, duration: 300 })
    }, 50)
    return () => window.clearTimeout(id)
  }, [layout, setNodes, setEdges, fitView])

  if (lectureNodes.length === 0) {
    return (
      <div
        style={{
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          height: '100%',
          color: 'var(--ink-4)',
          gap: 12,
          padding: 24,
          textAlign: 'center',
        }}
      >
        <div
          aria-hidden="true"
          style={{
            width: 64,
            height: 64,
            borderRadius: '50%',
            background: 'var(--bg-sunken)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
          }}
        >
          <Icon name="listChecks" size={28} />
        </div>
        <div>
          <h4 style={{ margin: 0, fontSize: 14, fontWeight: 700, color: 'var(--ink)' }}>
            Ouvindo a aula...
          </h4>
          <p style={{ margin: '6px 0 0', fontSize: 12.5 }}>
            Os tópicos da sua aula aparecerão aqui conforme o professor avança.
          </p>
        </div>
        {isProcessing ? <UpdatingChip /> : null}
      </div>
    )
  }

  return (
    <ReactFlow
      nodes={nodes}
      edges={edges}
      onNodesChange={onNodesChange}
      onEdgesChange={onEdgesChange}
      nodeTypes={nodeTypes}
      fitView
      fitViewOptions={{ padding: 0.2 }}
      proOptions={{ hideAttribution: true }}
      minZoom={0.2}
      maxZoom={2}
    >
      <Background gap={20} size={1} color="oklch(92% 0.005 270)" />
      <Controls showInteractive={false} />
      <div
        style={{
          position: 'absolute',
          top: 10,
          right: 10,
          display: 'flex',
          gap: 6,
          alignItems: 'center',
          zIndex: 5,
        }}
      >
        {isProcessing ? <UpdatingChip /> : null}
        <button
          aria-label={isFullscreen ? 'Sair da tela cheia' : 'Entrar em tela cheia'}
          className="icon-btn"
          onClick={onToggleFullscreen}
          style={{
            background: '#fff',
            border: '1px solid var(--line)',
            width: 30,
            height: 30,
            borderRadius: 8,
            boxShadow: '0 1px 3px rgba(0,0,0,0.05)',
          }}
          title={isFullscreen ? 'Sair da tela cheia' : 'Tela cheia'}
          type="button"
        >
          <Icon name={isFullscreen ? 'x' : 'arrowUpRight'} size={14} />
        </button>
      </div>
    </ReactFlow>
  )
}

function UpdatingChip() {
  return (
    <div
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: 6,
        padding: '5px 10px',
        borderRadius: 999,
        background: 'var(--warn-soft)',
        color: 'var(--warn)',
        fontSize: 11,
        fontWeight: 600,
        boxShadow: '0 1px 3px rgba(0,0,0,0.05)',
      }}
    >
      <span
        aria-hidden="true"
        style={{
          width: 9,
          height: 9,
          borderRadius: '50%',
          border: '2px solid currentColor',
          borderTopColor: 'transparent',
          animation: 'tree-spin 0.9s linear infinite',
          display: 'inline-block',
        }}
      />
      Atualizando...
    </div>
  )
}

type TreeViewerProps = {
  lectureNodes: LectureNode[]
  isProcessing?: boolean
  className?: string
  style?: React.CSSProperties
}

export function TreeViewer({ lectureNodes, isProcessing = false, className, style }: TreeViewerProps) {
  const [isFullscreen, setIsFullscreen] = useState(false)

  useEffect(() => {
    if (!isFullscreen) return
    const previous = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    return () => {
      document.body.style.overflow = previous
    }
  }, [isFullscreen])

  useEffect(() => {
    if (!isFullscreen) return
    function onKey(event: KeyboardEvent) {
      if (event.key === 'Escape') setIsFullscreen(false)
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [isFullscreen])

  const containerStyle: React.CSSProperties = isFullscreen
    ? {
        position: 'fixed',
        inset: 0,
        zIndex: 1000,
        background: '#fff',
      }
    : {
        position: 'relative',
        width: '100%',
        height: '100%',
        minHeight: 420,
        background: '#fff',
        borderRadius: 12,
        overflow: 'hidden',
        border: '1px solid var(--line)',
        ...style,
      }

  return (
    <div className={className} style={containerStyle}>
      <ReactFlowProvider>
        <TreeViewerInner
          lectureNodes={lectureNodes}
          isProcessing={isProcessing}
          isFullscreen={isFullscreen}
          onToggleFullscreen={() => setIsFullscreen((value) => !value)}
        />
      </ReactFlowProvider>
      <style>{`
        @keyframes tree-node-pulse {
          0% { transform: scale(1); }
          30% { transform: scale(1.04); }
          100% { transform: scale(1); }
        }
        @keyframes tree-spin {
          to { transform: rotate(360deg); }
        }
      `}</style>
    </div>
  )
}
