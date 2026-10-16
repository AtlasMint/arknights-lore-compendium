// Checks of the spoiler rule, the Episode tick chain, the fog and the stories layout. Run with: bun test
import { expect, test } from 'bun:test'
import { BANDS, GAP, forceBoxes, layoutStories, learnedIn, readable, toggleStory, uncovered, visibility, visibleGraph } from './lore.js'

const episodes = ['Prologue', 'Episode 01', 'Episode 02', 'Episode 03'].map((id, order) => ({ id, band: 'main', order }))
const stories = [...episodes, { id: 'Vigilo', band: 'collection', order: 9 }]

test('an Episode ticks the chain before it and unticks the chain after it', () => {
  let ticked = toggleStory(stories, new Set(), 'Episode 02')
  expect([...ticked].sort()).toEqual(['Episode 01', 'Episode 02', 'Prologue'])
  ticked = toggleStory(stories, ticked, 'Vigilo')
  ticked = toggleStory(stories, ticked, 'Episode 01')
  expect([...ticked].sort()).toEqual(['Prologue', 'Vigilo'])
})

test('a term shows if any of its stories is ticked; seeds always; untagged only with everything ticked', () => {
  const tags = { Talulah: ['Episode 01', 'Episode 08'], Kristen: ['Lone Trail'] }
  const rule = (ticked, everything = false, overrides = {}) =>
    visibility({ tags, ticked: new Set(ticked), everything, overrides, seeds: new Set(['Amiya']) })
  expect(rule(['Episode 08'])('Talulah')).toBe(true)
  expect(rule(['Episode 05'])('Talulah')).toBe(false)
  expect(rule([])('Amiya')).toBe(true)
  expect(rule(['Episode 05'])('Untagged')).toBe(false)
  expect(rule([], true)('Untagged')).toBe(true)
  expect(rule(['Lone Trail'], false, { Kristen: 'hide' })('Kristen')).toBe(false)
  expect(rule([], false, { Kristen: 'show' })('Kristen')).toBe(true)
  expect(rule([], false, { Amiya: 'hide' })('Amiya')).toBe(true) // the screenshot's own terms are never hidden
})

test('hidden nodes go with their links, and so does a node they leave alone', () => {
  const graph = {
    nodes: [
      { id: 'Amiya', seed: true, type: 'Operator' },
      { id: 'Talulah', type: 'Character' },
      { id: 'Alina', type: 'Character' },
    ],
    links: [
      { source: 'Amiya', target: 'Talulah' },
      { source: 'Talulah', target: 'Alina' },
    ],
  }
  const shown = visibleGraph(graph, (t) => t !== 'Talulah', new Set(['Operator', 'Character']))
  expect(shown.nodes.map((n) => n.id)).toEqual(['Amiya'])
  expect(shown.links).toEqual([])
})

test('a label shows with the first ticked story both ends share', () => {
  const link = { stories: ['Episode 04', 'Episode 07'] }
  expect(learnedIn(link, new Set(['Episode 07']), false)).toEqual({ story: 'Episode 07' })
  expect(learnedIn(link, new Set(['Episode 01']), false)).toBe(null)
  expect(learnedIn({ stories: [] }, new Set(), true)).toEqual({ story: null })
})

test('a summary sentence waits for the story that told it, or for its terms when no story did', () => {
  const summary = [
    { text: 'profile', terms: [], story: null },
    { text: 'rescued by the Doctor', terms: ['Doctor'], story: 'Babel (event)' },
    { text: 'met Talulah', terms: ['Talulah'], story: null },
  ]
  const isVisible = (term) => term === 'Doctor'
  const texts = (ticked, everything) => readable(summary, { ticked, everything, isVisible }).map((s) => s.text)
  expect(texts(new Set(), false)).toEqual(['profile']) // the Doctor is visible, but Babel is unread
  expect(texts(new Set(['Babel (event)']), false)).toEqual(['profile', 'rescued by the Doctor'])
  expect(texts(new Set(), true)).toEqual(['profile', 'rescued by the Doctor']) // tick all: the story rule lifts, the term rule is the caller's
})

test('overlapping boxes are pushed apart along the axis that needs the smaller move, others left alone', () => {
  const box = () => ({ x0: -10, x1: 50, y0: -10, y1: 10 }) // a node with its name to the right
  const nodes = [
    { x: 0, y: 0, vx: 0, vy: 0 },
    { x: 40, y: 5, vx: 0, vy: 0 }, // overlaps the first by 20 along x and 15 along y
    { x: 0, y: 100, vx: 0, vy: 0 }, // clear of both
  ]
  const force = forceBoxes(box, 1)
  force.initialize(nodes)
  force()
  expect(nodes.map((n) => [n.vx, n.vy])).toEqual([
    [0, -7.5], // the y overlap is the smaller: the upper one goes up, the lower down, half each
    [0, 7.5],
    [0, 0],
  ])
})

test('the fog leaves only the stories read, where storylines start, and the one step after either', () => {
  // Prologue -> Episode 01 -> Episode 02 -> Episode 03; a side story follows Episode 02; Vigilo stands alone.
  const data = {
    stories: [...stories, { id: 'Side', band: 'side', order: 5 }],
    acts: [],
    edges: [
      { source: 'Prologue', target: 'Episode 01', kind: 'sequel' },
      { source: 'Episode 01', target: 'Episode 02', kind: 'sequel' },
      { source: 'Episode 02', target: 'Episode 03', kind: 'sequel' },
      { source: 'Episode 02', target: 'Side', kind: 'related' },
    ],
  }
  expect([...uncovered(data, new Set())].sort()).toEqual(['Episode 01', 'Prologue', 'Vigilo'])
  const read = toggleStory(data.stories, new Set(), 'Episode 02')
  expect([...uncovered(data, read)].sort()).toEqual(['Episode 01', 'Episode 02', 'Episode 03', 'Prologue', 'Side', 'Vigilo'])
})

test('no two story nodes overlap or sit closer than the gap, on either tab, with or without a Movement picked', () => {
  // Thirty stories crowded into two years, some sharing a day, across every band and two Movements.
  const many = Array.from({ length: 30 }, (_, i) => ({
    id: `S${i}`,
    name: `Story number ${i}`,
    band: BANDS[i % 5][0],
    movement: i % 5 === 4 ? null : i % 2 ? 'AE' : 'MS',
    start: `202${i % 2}-0${1 + (i % 3)}-1${i % 4}`,
    year: i % 3 ? `ca. 109${5 + (i % 5)}` : null,
    order: i,
  }))
  const data = { stories: many, acts: [], edges: [{ source: 'S0', target: 'S1', kind: 'related' }] }
  for (const tab of ['release', 'ingame']) {
    for (const movement of ['', 'MS']) {
      const { items, edges } = layoutStories(data, { tab, movement, measure: (text) => text.length * 6 })
      for (const a of items) {
        for (const b of items) {
          const apart = a === b || a.y !== b.y || a.x + a.w + GAP <= b.x || b.x + b.w + GAP <= a.x
          expect(apart).toBe(true)
        }
      }
      expect(edges.map((e) => e.ends.map((end) => end.id).sort())).toEqual([['S0', 'S1']]) // each end knows its story
      if (movement) expect(items.filter((s) => s.faded).map((s) => s.id)).toEqual(['S1'])
    }
  }
})
