/**
 * Post-render enhancer for the "Optimization Trigger Flow" diagram on the
 * Authentication & Permissions page.
 *
 * Mermaid cannot draw node-to-node connectors across a 3x3 grid: any edge whose
 * endpoint is a node inside a `direction LR` subgraph makes Mermaid drop that
 * subgraph's direction and collapse the grid to a vertical stack (true for both
 * the dagre and ELK engines). So the diagram source keeps the grid via
 * subgraph-to-subgraph links (`r1 --> r2 --> r3`), which render as generic
 * centered down-arrows.
 *
 * This module runs after Mermaid renders and replaces those two center arrows
 * with true elbow (orthogonal) connectors that go node-to-node:
 *   step 1 -> 2  (s1, end of row 1  ->  s2, start of row 2)
 *   step 4 -> 5  (s4, end of row 2  ->  s5, start of row 3)
 *
 * It is defensive: if the expected nodes/marker aren't found it does nothing and
 * leaves Mermaid's default arrows intact (graceful degradation).
 */
import ExecutionEnvironment from '@docusaurus/ExecutionEnvironment';

const SVG_NS = 'http://www.w3.org/2000/svg';

// Map an element's local edge-midpoints into `target`'s coordinate space, so the
// new <path> (appended under `target`) lines up with the rendered nodes
// regardless of the cluster-subgroup nesting Mermaid uses for subgraphs.
function anchorMapper(target, el) {
  const m = target.getScreenCTM().inverse().multiply(el.getScreenCTM());
  const b = el.getBBox();
  const pt = (lx, ly) => new DOMPoint(lx, ly).matrixTransform(m);
  const cx = b.x + b.width / 2;
  return {
    cx,
    topC: pt(cx, b.y),
    bottomC: pt(cx, b.y + b.height),
  };
}

// Forward extent of the arrowhead past the path endpoint, in user units. The
// pointEnd marker is center-anchored (refX in the middle of its viewBox), so its
// tip reaches markerWidth*(1 - refX/viewBoxWidth) beyond the endpoint. Ending the
// elbow this far above the target box top makes the whole arrowhead clear the node
// (which paints above edges) with the tip touching the box, like Mermaid's own edges.
function markerInset(svg) {
  const FALLBACK = 4;
  const m = svg.querySelector('marker[id*="pointEnd"]:not([id*="margin"])');
  if (!m) return FALLBACK;
  const mw = parseFloat(m.getAttribute('markerWidth'));
  const refX = parseFloat(m.getAttribute('refX'));
  const vbW = parseFloat((m.getAttribute('viewBox') || '0 0 10 10').split(/\s+/)[2]);
  if (!isFinite(mw) || !isFinite(refX) || !isFinite(vbW) || vbW === 0) return FALLBACK;
  return mw * (1 - refX / vbW);
}

// Find a node group's box rect within an SVG by the node-id suffix Mermaid emits
// (e.g. "...-flowchart-s1-2"); returns the <rect> used for geometry.
function nodeRect(svg, key) {
  const g = svg.querySelector(`g.node[id*="-flowchart-${key}-"]`);
  return g ? g.querySelector('rect.label-container') || g.querySelector('rect') : null;
}

function elbowPath(d, markerEnd) {
  const p = document.createElementNS(SVG_NS, 'path');
  p.setAttribute('d', d);
  p.setAttribute('class', 'flowchart-link gw-elbow-edge');
  p.setAttribute('fill', 'none');
  p.setAttribute('stroke-linejoin', 'round');
  if (markerEnd) p.setAttribute('marker-end', markerEnd);
  return p;
}

function enhanceSvg(svg) {
  if (svg.dataset.elbowed) return;

  const edgePaths = svg.querySelector('g.edgePaths');
  if (!edgePaths) return;

  // Reuse the themed arrowhead marker from any existing edge.
  const sample = edgePaths.querySelector('path.flowchart-link[marker-end]');
  const markerEnd = sample && sample.getAttribute('marker-end');
  const inset = markerInset(svg);

  // The two wrap connectors we want: [source, target] node keys.
  const pairs = [
    ['s1', 's2'],
    ['s4', 's5'],
  ];

  const built = [];
  for (const [from, to] of pairs) {
    const fromRect = nodeRect(svg, from);
    const toRect = nodeRect(svg, to);
    if (!fromRect || !toRect) return; // bail; leave defaults intact

    const a = anchorMapper(edgePaths, fromRect).bottomC; // leave source bottom
    const b = anchorMapper(edgePaths, toRect).topC; // enter target top
    const midY = (a.y + b.y) / 2;
    const endY = b.y - inset; // stop short so the arrowhead clears the target node
    // Orthogonal "staple": down into the inter-row gap, across, down into target.
    const d = `M${a.x},${a.y} L${a.x},${midY} L${b.x},${midY} L${b.x},${endY}`;
    built.push(elbowPath(d, markerEnd));
  }

  // Only now (all anchors resolved) hide the default center arrows and draw ours.
  const defaults = ['L_r1_r2_0', 'L_r2_r3_0']
    .map((id) => svg.querySelector(`[data-id="${id}"]`))
    .filter(Boolean);
  if (defaults.length !== 2) return;

  defaults.forEach((p) => {
    p.style.display = 'none';
  });
  built.forEach((p) => edgePaths.appendChild(p));
  svg.dataset.elbowed = '1';
}

function enhanceAll() {
  // Scope to the trigger-flow diagram: it uniquely contains an `s5` node.
  document
    .querySelectorAll('.docusaurus-mermaid-container svg:not([data-elbowed])')
    .forEach((svg) => {
      if (svg.querySelector('g.node[id*="-flowchart-s5-"]')) {
        try {
          enhanceSvg(svg);
        } catch (_e) {
          /* leave Mermaid's default rendering untouched on any error */
        }
      }
    });
}

if (ExecutionEnvironment.canUseDOM) {
  let scheduled = false;
  const schedule = () => {
    if (scheduled) return;
    scheduled = true;
    requestAnimationFrame(() => {
      scheduled = false;
      enhanceAll();
    });
  };
  // Catches Mermaid's async render, SPA navigation, and the theme-toggle
  // re-render (which swaps in a fresh, unflagged SVG). The data-elbowed flag
  // makes this idempotent, so our own DOM writes don't cause a loop.
  const observer = new MutationObserver(schedule);
  const start = () =>
    observer.observe(document.body, {childList: true, subtree: true});
  if (document.body) start();
  else window.addEventListener('DOMContentLoaded', start);
}

export function onRouteDidUpdate() {
  if (ExecutionEnvironment.canUseDOM) requestAnimationFrame(enhanceAll);
}
