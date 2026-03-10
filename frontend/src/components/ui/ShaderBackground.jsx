import { useRef, useEffect, useCallback } from 'react'

const vertexShader = `
  attribute vec2 position;
  void main() {
    gl_Position = vec4(position, 0.0, 1.0);
  }
`

const fragmentShader = `
  precision mediump float;
  uniform float u_time;
  uniform vec2 u_resolution;

  // Simplex-ish noise
  vec3 mod289(vec3 x) { return x - floor(x * (1.0/289.0)) * 289.0; }
  vec2 mod289(vec2 x) { return x - floor(x * (1.0/289.0)) * 289.0; }
  vec3 permute(vec3 x) { return mod289(((x*34.0)+1.0)*x); }

  float snoise(vec2 v) {
    const vec4 C = vec4(0.211324865405187, 0.366025403784439,
                       -0.577350269189626, 0.024390243902439);
    vec2 i  = floor(v + dot(v, C.yy));
    vec2 x0 = v - i + dot(i, C.xx);
    vec2 i1 = (x0.x > x0.y) ? vec2(1.0, 0.0) : vec2(0.0, 1.0);
    vec4 x12 = x0.xyxy + C.xxzz;
    x12.xy -= i1;
    i = mod289(i);
    vec3 p = permute(permute(i.y + vec3(0.0, i1.y, 1.0)) + i.x + vec3(0.0, i1.x, 1.0));
    vec3 m = max(0.5 - vec3(dot(x0,x0), dot(x12.xy,x12.xy), dot(x12.zw,x12.zw)), 0.0);
    m = m*m; m = m*m;
    vec3 x = 2.0 * fract(p * C.www) - 1.0;
    vec3 h = abs(x) - 0.5;
    vec3 ox = floor(x + 0.5);
    vec3 a0 = x - ox;
    m *= 1.79284291400159 - 0.85373472095314 * (a0*a0 + h*h);
    vec3 g;
    g.x = a0.x * x0.x + h.x * x0.y;
    g.yz = a0.yz * x12.xz + h.yz * x12.yw;
    return 130.0 * dot(m, g);
  }

  void main() {
    vec2 uv = gl_FragCoord.xy / u_resolution;
    float t = u_time * 0.15;

    // Layered noise for plasma effect
    float n1 = snoise(uv * 3.0 + t * 0.5);
    float n2 = snoise(uv * 5.0 - t * 0.3);
    float n3 = snoise(uv * 2.0 + vec2(t * 0.2, -t * 0.4));

    float plasma = (n1 + n2 * 0.5 + n3 * 0.25) * 0.5 + 0.5;

    // Red/purple/cyan color palette matching theme
    vec3 red = vec3(0.94, 0.27, 0.27);
    vec3 purple = vec3(0.55, 0.36, 0.96);
    vec3 cyan = vec3(0.02, 0.71, 0.83);
    vec3 dark = vec3(0.02, 0.02, 0.03);

    vec3 color = mix(dark, red, smoothstep(0.3, 0.7, plasma) * 0.08);
    color = mix(color, purple, smoothstep(0.4, 0.8, n2 * 0.5 + 0.5) * 0.06);
    color = mix(color, cyan, smoothstep(0.5, 0.9, n3 * 0.5 + 0.5) * 0.04);

    // Grid overlay
    vec2 grid = fract(uv * vec2(u_resolution.x / 60.0, u_resolution.y / 60.0));
    float gridLine = step(0.97, grid.x) + step(0.97, grid.y);
    color += gridLine * 0.015;

    // Vignette
    float vignette = 1.0 - length((uv - 0.5) * 1.5);
    color *= smoothstep(0.0, 0.7, vignette);

    gl_FragColor = vec4(color, 1.0);
  }
`

function initWebGL(canvas) {
  const gl = canvas.getContext('webgl', { alpha: false, antialias: false })
  if (!gl) return null

  const vs = gl.createShader(gl.VERTEX_SHADER)
  gl.shaderSource(vs, vertexShader)
  gl.compileShader(vs)

  const fs = gl.createShader(gl.FRAGMENT_SHADER)
  gl.shaderSource(fs, fragmentShader)
  gl.compileShader(fs)

  const program = gl.createProgram()
  gl.attachShader(program, vs)
  gl.attachShader(program, fs)
  gl.linkProgram(program)
  gl.useProgram(program)

  const vertices = new Float32Array([-1, -1, 1, -1, -1, 1, 1, 1])
  const buffer = gl.createBuffer()
  gl.bindBuffer(gl.ARRAY_BUFFER, buffer)
  gl.bufferData(gl.ARRAY_BUFFER, vertices, gl.STATIC_DRAW)

  const pos = gl.getAttribLocation(program, 'position')
  gl.enableVertexAttribArray(pos)
  gl.vertexAttribPointer(pos, 2, gl.FLOAT, false, 0, 0)

  return {
    gl,
    uniforms: {
      time: gl.getUniformLocation(program, 'u_time'),
      resolution: gl.getUniformLocation(program, 'u_resolution'),
    },
  }
}

export default function ShaderBackground() {
  const canvasRef = useRef(null)
  const ctxRef = useRef(null)
  const rafRef = useRef(null)

  const resize = useCallback(() => {
    const canvas = canvasRef.current
    if (!canvas || !ctxRef.current) return
    const dpr = Math.min(window.devicePixelRatio, 1.5)
    canvas.width = window.innerWidth * dpr
    canvas.height = window.innerHeight * dpr
    ctxRef.current.gl.viewport(0, 0, canvas.width, canvas.height)
  }, [])

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return

    const ctx = initWebGL(canvas)
    if (!ctx) return
    ctxRef.current = ctx

    resize()
    window.addEventListener('resize', resize)

    const start = performance.now()
    const render = () => {
      const { gl, uniforms } = ctx
      const t = (performance.now() - start) / 1000
      gl.uniform1f(uniforms.time, t)
      gl.uniform2f(uniforms.resolution, canvas.width, canvas.height)
      gl.drawArrays(gl.TRIANGLE_STRIP, 0, 4)
      rafRef.current = requestAnimationFrame(render)
    }
    rafRef.current = requestAnimationFrame(render)

    return () => {
      window.removeEventListener('resize', resize)
      if (rafRef.current) cancelAnimationFrame(rafRef.current)
    }
  }, [resize])

  return (
    <canvas
      ref={canvasRef}
      className="fixed inset-0 w-full h-full"
      style={{ zIndex: -1, pointerEvents: 'none' }}
    />
  )
}
