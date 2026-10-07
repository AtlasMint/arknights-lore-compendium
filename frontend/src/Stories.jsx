import { useMemo, useState } from 'react'
import { layoutStories, toggleStory, uncovered } from './lore.js'

let context
// A label's width in pixels, in the canvas's own font.
function measure(text) {
  context ??= document.createElement('canvas').getContext('2d')
  context.font = '12px system-ui, sans-serif'
  return context.measureText(text).width
}

const DATE = new Intl.DateTimeFormat(undefined, { dateStyle: 'medium', timeZone: 'UTC' })

// Every story released on Global, on one canvas: click to tick what you have read. Ticks are what the lore map shows.
// With the fog on, only read stories, storyline starts and the one step after either are drawn.
export default function Stories({ data, ticked, onTicked, fog, onFog }) {
  const [tab, setTab] = useState('release')
  const [movement, setMovement] = useState('')
  const [focus, setFocus] = useState(null)
  const layout = useMemo(() => layoutStories(data, { tab, movement, measure }), [data, tab, movement])
  const names = useMemo(() => Object.fromEntries(data.movements.map((m) => [m.code, m.name])), [data])
  const clear = useMemo(() => (fog ? uncovered(data, ticked) : null), [fog, data, ticked]) // null draws them all
  const shown = (id) => !clear || clear.has(id)
  const items = layout.items.filter((s) => shown(s.id))
  // An edge with one end in the fog fades out towards it; one with both ends there isn't drawn.
  const edges = layout.edges.filter((e) => e.ends.some((end) => shown(end.id)))
  const lit = focus && new Set([focus, ...layout.edges.flatMap((e) => (e.source === focus ? [e.target] : e.target === focus ? [e.source] : []))])
  const tick = (id) => onTicked(toggleStory(data.stories, ticked, id))

  return (
    <section className="stories" aria-label="Stories you have read">
      <div className="controls">
        <div role="tablist" aria-label="Order stories by">
          {[
            ['release', 'Release'],
            ['ingame', 'In-game'],
          ].map(([key, label]) => (
            <button key={key} role="tab" aria-selected={tab === key} onClick={() => setTab(key)}>
              {label}
            </button>
          ))}
        </div>
        <span>
          {data.stories.filter((s) => ticked.has(s.id)).length} of {data.stories.length} read
        </span>
        <button onClick={() => onTicked(new Set(data.stories.map((s) => s.id)))}>Tick all (spoilers)</button>
        <button onClick={() => onTicked(new Set())}>Untick all</button>
        <button
          aria-pressed={fog}
          title="Cover all future stories not yet encountered. Only what you have read, the start of each storyline and the one step after them stay on the canvas."
          onClick={() => onFog(!fog)}
        >
          Fog of the Future
        </button>
      </div>
      <div className="controls movements" role="group" aria-label="Movement">
        <button aria-pressed={!movement} onClick={() => setMovement('')}>
          All Movements
        </button>
        {data.movements.map((m) => (
          <button key={m.code} aria-pressed={movement === m.code} title={m.intro} onClick={() => setMovement(m.code)}>
            <img className="icon" src={`/icon/${m.code}`} alt="" width="18" height="18" />
            {m.name}
          </button>
        ))}
      </div>
      <div className="canvas">
        <svg
          width={layout.width}
          height={layout.height}
          role="group"
          aria-label={clear ? `${items.length} of ${layout.items.length} stories, the rest covered by the fog` : `${layout.items.length} stories`}
        >
          {clear && (
            <defs>
              {edges.map((e, i) => {
                const [near, far] = shown(e.ends[0].id) ? e.ends : [e.ends[1], e.ends[0]]
                return shown(far.id) ? null : (
                  <linearGradient key={i} id={`fog-${i}`} className="fog" gradientUnits="userSpaceOnUse" x1={near.x} y1={near.y} x2={far.x} y2={far.y}>
                    <stop offset="0" stopOpacity="0.7" />
                    <stop offset="1" stopOpacity="0" />
                  </linearGradient>
                )
              })}
            </defs>
          )}
          {layout.ticks.map((t) => (
            <g key={t.label} className="tick">
              <line x1={t.x} x2={t.x} y1={14} y2={layout.height} />
              <text x={t.x + 3} y={12}>
                {t.label}
              </text>
            </g>
          ))}
          {layout.bands.map((b) => (
            <g key={b.key} className="band">
              <rect x={0} y={b.y} width={layout.width} height={b.h} />
              <text x={4} y={b.y + 15}>
                {b.label}
              </text>
            </g>
          ))}
          {layout.acts
            .filter((a) => shown(a.first))
            .map((a) => (
              <text key={a.name} className="act" x={a.x} y={a.y}>
                {a.name}
              </text>
            ))}
          {edges.map((e, i) => (
            <path
              key={`${e.source}\n${e.target}`}
              className={`edge ${e.kind}${focus ? (e.source === focus || e.target === focus ? ' lit' : ' dim') : ''}`}
              style={e.ends.every((end) => shown(end.id)) ? undefined : { stroke: `url(#fog-${i})` }}
              d={e.d}
            />
          ))}
          {items.map((s) => (
            <g
              key={s.id}
              className={`story${ticked.has(s.id) ? ' ticked' : ''}${s.faded ? ' faded' : ''}${lit && !lit.has(s.id) ? ' dim' : ''}`}
              transform={`translate(${s.x},${s.y})`}
              role="button"
              tabIndex={0}
              aria-pressed={ticked.has(s.id)}
              aria-label={`${s.name}${s.subtitle ? `: ${s.subtitle}` : ''}, ${ticked.has(s.id) ? 'read' : 'not read'}`}
              onClick={() => tick(s.id)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                  e.preventDefault()
                  tick(s.id)
                }
              }}
              onMouseEnter={() => setFocus(s.id)}
              onMouseLeave={() => setFocus(null)}
              onFocus={() => setFocus(s.id)}
              onBlur={() => setFocus(null)}
            >
              <title>
                {[
                  s.subtitle ? `${s.name}: ${s.subtitle}` : s.name,
                  `${names[s.movement] ?? 'Crossover, non-canon'} · Global ${DATE.format(new Date(s.start))} · in-game ${s.year ?? 'undated'}`,
                  s.teaser,
                ]
                  .filter(Boolean)
                  .join('\n')}
              </title>
              <rect width={s.w} height={layout.node} rx={4} />
              {s.movement && <image className="icon" href={`/icon/${s.movement}`} x={4} y={2} width={18} height={18} />}
              <text x={s.movement ? 26 : 8} y={15}>
                {ticked.has(s.id) ? '✓ ' : ''}
                {s.name}
              </text>
            </g>
          ))}
        </svg>
      </div>
    </section>
  )
}
