import * as d3 from 'd3'
import { useEffect, useRef, useState } from 'react'

export default function App() {
  const [seeds, setSeeds] = useState('Amiya, Reunion')
  const [depth, setDepth] = useState(2)
  const [graph, setGraph] = useState(null)
  const [status, setStatus] = useState('')

  async function build(event) {
    event.preventDefault()
    setStatus('Building… a cold cache takes several seconds.')
    const response = await fetch(`/graph?${new URLSearchParams({ seeds, depth })}`).catch(() => null)
    const body = await response?.json().catch(() => null)
    if (!response?.ok || !body) {
      setStatus(body?.error ?? `Backend unreachable or failed (${response?.status ?? 'no response'}).`)
      return
    }
    setGraph(body)
    setStatus(`${body.nodes.length} nodes, ${body.links.length} links`)
  }

  return (
    <>
      <form onSubmit={build}>
        <label>
          Seeds <input value={seeds} onChange={(e) => setSeeds(e.target.value)} size={36} required />
        </label>
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
