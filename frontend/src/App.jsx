import * as d3 from 'd3'
import { useEffect, useRef, useState } from 'react'

export default function App() {
  // Keywords to seed the graph with. Only chips that are on are sent; the rest wait for the user to decide.
  const [chips, setChips] = useState([
    { title: 'Amiya', on: true },
    { title: 'Reunion', on: true },
  ])
  const [draft, setDraft] = useState('')
  const [suggestions, setSuggestions] = useState([])
  const [preview, setPreview] = useState(null)
  const [reading, setReading] = useState(null)
  const [depth, setDepth] = useState(1)
  const [graph, setGraph] = useState(null)
  const [status, setStatus] = useState('')

  // JSON from the backend, or null after putting the reason in the status line.
  async function api(url, options) {
    const response = await fetch(url, options).catch(() => null)
    const body = await response?.json().catch(() => null)
    if (response?.ok && body) return body
    setStatus(body?.error ?? `Backend unreachable or failed (${response?.status ?? 'no response'}).`)
    return null
  }

  // The reader's time grows with pixels: a 2340×1080 phone screenshot took 19 s, at 1280 px wide 6 s,
  // and the dialog text is still legible. Anything that isn't an image is sent as is, for the server's 415.
  async function shrink(file, maxSide = 1280) {
    const bitmap = await createImageBitmap(file).catch(() => null)
    if (!bitmap || Math.max(bitmap.width, bitmap.height) <= maxSide) return file
    const scale = maxSide / Math.max(bitmap.width, bitmap.height)
    const canvas = new OffscreenCanvas(Math.round(bitmap.width * scale), Math.round(bitmap.height * scale))
    canvas.getContext('2d').drawImage(bitmap, 0, 0, canvas.width, canvas.height)
    return canvas.convertToBlob({ type: 'image/png' })
  }

  async function analyze(file) {
    if (!file) return
    URL.revokeObjectURL(preview)
    setPreview(URL.createObjectURL(file))
    setReading(null)
    setStatus('Reading the screenshot…')
    const form = new FormData()
    form.append('image', await shrink(file), 'screenshot.png')
    const body = await api('/analyze', { method: 'POST', body: form })
    if (!body) return
    setReading(body)
    setChips([
      ...body.keywords.map((title) => ({ title, on: true })),
      ...body.needs_context.map((title) => ({ title, on: false })),
    ])
    setStatus(
      body.keywords.length || body.needs_context.length
        ? 'Click a keyword to include or leave it out (dashed ones are left out), then build the graph.'
        : 'No wiki terms found. Add keywords by hand.',
    )
  }

  async function suggest(value) {
    setDraft(value)
    if (value.trim().length < 2) return
    const response = await fetch(`/terms?${new URLSearchParams({ prefix: value.trim() })}`).catch(() => null)
    setSuggestions((await response?.json().catch(() => null)) ?? [])
  }

  function add(event) {
    event.preventDefault()
    const titles = draft.split(',').map((t) => t.trim()).filter(Boolean)
    setChips([...chips.filter((c) => !titles.includes(c.title)), ...titles.map((title) => ({ title, on: true }))])
    setDraft('')
  }

  async function build(event) {
    event.preventDefault()
    const seeds = chips.filter((c) => c.on).map((c) => c.title).join(',')
    setStatus('Building… a cold cache takes several seconds.')
    const body = await api(`/graph?${new URLSearchParams({ seeds, depth, speaker: reading?.speaker ?? '' })}`)
    if (!body) return
    setGraph(body)
    setStatus(`${body.nodes.length} nodes, ${body.links.length} links`)
  }

  return (
    <>
      <header>
        <div>
          <label
            className="drop"
            onDragOver={(e) => e.preventDefault()}
            onDrop={(e) => {
              e.preventDefault()
              analyze(e.dataTransfer.files[0])
            }}
          >
            Drop a dialog screenshot here, or{' '}
            <input type="file" accept="image/png,image/jpeg,image/webp" onChange={(e) => analyze(e.target.files[0])} />
          </label>
          {preview && <img className="preview" src={preview} alt="The uploaded screenshot" />}
          {reading && (
            <p className="reading">
              <b>{reading.speaker || 'No speaker'}:</b> {reading.text}
            </p>
          )}
        </div>
        <form onSubmit={add} aria-label="Keywords">
          {chips.map((chip, i) => (
            <button
              key={chip.title}
              type="button"
              className="chip"
              aria-pressed={chip.on}
              onClick={() => setChips(chips.map((c, j) => (i === j ? { ...c, on: !c.on } : c)))}
            >
              {chip.title}
            </button>
          ))}
          <input
            list="terms"
            value={draft}
            onChange={(e) => suggest(e.target.value)}
            placeholder="Add a keyword"
            aria-label="Add a keyword"
          />
          <datalist id="terms">
            {suggestions.map((t) => (
              <option key={t} value={t} />
            ))}
          </datalist>
          <button>Add</button>
        </form>
        <form onSubmit={build}>
          <label>
            Depth{' '}
            <select value={depth} onChange={(e) => setDepth(Number(e.target.value))}>
              {[1, 2, 3].map((d) => (
                <option key={d}>{d}</option>
              ))}
            </select>
          </label>
          <button>Build graph</button>
          <output>{status}</output>
        </form>
      </header>
      {graph && <Graph data={graph} />}
    </>
  )
}

function Graph({ data }) {
  const svgRef = useRef(null)

  useEffect(() => {
    const svg = d3.select(svgRef.current)
    const { width, height } = svgRef.current.getBoundingClientRect()
    const nodes = data.nodes.map((d) => ({ ...d })) // the simulation mutates these
    const links = data.links.map((d) => ({ ...d }))
    const radius = d3.scaleSqrt().domain(d3.extent(nodes, (d) => d.score)).range([4, 18])

    const root = svg.append('g')
    svg.call(d3.zoom().scaleExtent([0.2, 8]).on('zoom', (event) => root.attr('transform', event.transform)))

    const link = root
      .append('g')
      .attr('class', 'links')
      .selectAll('line')
      .data(links)
      .join('line')
      .attr('stroke-width', (d) => Math.sqrt(d.weight))
    const node = root
      .append('g')
      .selectAll('g')
      .data(nodes)
      .join('g')
      .attr('class', (d) => (d.seed ? 'node seed' : 'node'))
    node.append('circle').attr('r', (d) => radius(d.score))
    node
      .append('text')
      .text((d) => d.id)
      .attr('x', (d) => radius(d.score) + 3)
      .attr('dy', '0.35em')
    node.append('title').text((d) => [d.id, ...d.categories].join('\n'))
    node.filter((d) => d.seed).raise()

    const simulation = d3
      .forceSimulation(nodes)
      .force('link', d3.forceLink(links).id((d) => d.id).distance(70))
      .force('charge', d3.forceManyBody().strength(-160))
      .force('collide', d3.forceCollide((d) => radius(d.score) + 2))
      .force('center', d3.forceCenter(width / 2, height / 2))
      .on('tick', () => {
        link
          .attr('x1', (d) => d.source.x)
          .attr('y1', (d) => d.source.y)
          .attr('x2', (d) => d.target.x)
          .attr('y2', (d) => d.target.y)
        node.attr('transform', (d) => `translate(${d.x},${d.y})`)
      })

    node.call(
      d3
        .drag()
        .on('start', (event, d) => {
          if (!event.active) simulation.alphaTarget(0.3).restart()
          d.fx = d.x
          d.fy = d.y
        })
        .on('drag', (event, d) => {
          d.fx = event.x
          d.fy = event.y
        })
        .on('end', (event, d) => {
          if (!event.active) simulation.alphaTarget(0)
          d.fx = null
          d.fy = null
        }),
    )

    return () => {
      simulation.stop()
      svg.on('.zoom', null)
      root.remove()
    }
  }, [data])

  return <svg ref={svgRef} role="img" aria-label={`Lore graph of ${data.nodes.length} wiki pages`} />
}
