# Playwright fixtures

Self-contained inputs for the E2E suite. Nothing here is fetched from the
network at test time.

## Files

### `cube.stl` (684 bytes, binary STL)

A unit cube (8 vertices, 12 triangles) with outward face normals. Used by
`truth-gate-tab.spec.ts` to drive the Truth Gate validator. Chosen because it
is the smallest geometrically valid mesh that passes most Truth Gate checks
(manifold, watertight, non-zero volume, consistent normals).

### `console-strict.ts`

A Playwright fixture (`auto: true`) that fails the test if the page emits any
of: a `pageerror`, a `console.error` call, a `requestfailed` event, or an HTTP
response with status >= 400. URL exclusions are documented inline.

## Regenerating

### `cube.stl`

```bash
python -c "
import struct
v = [(0,0,0),(1,0,0),(1,1,0),(0,1,0),(0,0,1),(1,0,1),(1,1,1),(0,1,1)]
tris = [
  ((0,0,-1),0,2,1),((0,0,-1),0,3,2),
  ((0,0, 1),4,5,6),((0,0, 1),4,6,7),
  ((0,-1,0),0,1,5),((0,-1,0),0,5,4),
  ((1,0, 0),1,2,6),((1,0, 0),1,6,5),
  ((0,1, 0),2,3,7),((0,1, 0),2,7,6),
  ((-1,0,0),3,0,4),((-1,0,0),3,4,7),
]
out = b'Hermes3D unit cube fixture - generated for Playwright tests'.ljust(80, b'\0')
out += struct.pack('<I', 12)
for n, a, b, c in tris:
    out += struct.pack('<3f', *n)
    out += struct.pack('<3f', *v[a])
    out += struct.pack('<3f', *v[b])
    out += struct.pack('<3f', *v[c])
    out += struct.pack('<H', 0)
open('cube.stl','wb').write(out)
"
```

The script is deterministic; rerunning it produces a byte-identical file.
