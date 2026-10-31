// Перламутр, зелёная сфера: команде больше нравится Созвездие, поэтому в интерфейсе не используется.
import type { OrbRenderer } from '../Orb'

const VERTEX = 'attribute vec2 p;void main(){gl_Position=vec4(p,0.,1.);}'
const FRAGMENT = `precision highp float;uniform vec2 r;uniform float t,a,m;
vec3 h(vec3 p){p=vec3(dot(p,vec3(127.1,311.7,74.7)),dot(p,vec3(269.5,183.3,246.1)),dot(p,vec3(113.5,271.9,124.6)));return -1.+2.*fract(sin(p)*43758.5453);}
float n(vec3 p){vec3 i=floor(p),f=fract(p),u=f*f*(3.-2.*f);
 return mix(mix(mix(dot(h(i),f),dot(h(i+vec3(1,0,0)),f-vec3(1,0,0)),u.x),mix(dot(h(i+vec3(0,1,0)),f-vec3(0,1,0)),dot(h(i+vec3(1,1,0)),f-vec3(1,1,0)),u.x),u.y),
            mix(mix(dot(h(i+vec3(0,0,1)),f-vec3(0,0,1)),dot(h(i+vec3(1,0,1)),f-vec3(1,0,1)),u.x),mix(dot(h(i+vec3(0,1,1)),f-vec3(0,1,1)),dot(h(i+vec3(1,1,1)),f-vec3(1,1,1)),u.x),u.y),u.z);}
float fb(vec3 p){return .6*n(p)+.3*n(p*2.03+3.1)+.1*n(p*4.1+7.);}
void main(){vec2 q=(gl_FragCoord.xy*2.-r)/min(r.x,r.y);
 float tt=t*(.22+.5*m);
 float ang=atan(q.y,q.x),wob=(.035+.11*a)*n(vec3(cos(ang)*1.3,sin(ang)*1.3,t*(.5+1.6*a)));
 float R=.8+.05*a+wob,d=length(q);
 float edge=smoothstep(R,R-.012,d);
 if(edge<=0.){gl_FragColor=vec4(0.);return;}
 float z=sqrt(max(0.,1.-min(1.,d*d/(R*R))));
 vec3 N=normalize(vec3(q/R,z));
 vec3 P=N*(.72+.3*a)+vec3(0.,0.,tt);
 float w=fb(P+.7*fb(P*1.2-tt*.7))-.16*q.y/R;
 vec3 g=vec3(.055,.48,.33),te=vec3(.36,.78,.68),pe=vec3(.94,.97,.93),am=vec3(.91,.76,.42);
 vec3 col=mix(pe,te,smoothstep(-.3,.3,w));
 col=mix(col,g,smoothstep(.12,.62,w)*.85);
 col=mix(col,am,smoothstep(.12,.5,-w)*.32);
 float fr=pow(1.-z,2.4);
 col=mix(col,vec3(.96,.99,.97),fr*.75);
 col+=pow(max(0.,dot(N,normalize(vec3(-.45,.6,.75)))),26.)*.5;
 col*=.95+.09*N.y;
 gl_FragColor=vec4(col*edge,edge);}`

export function createPearl(canvas: HTMLCanvasElement): OrbRenderer | null {
  const gl = canvas.getContext('webgl', { alpha: true, premultipliedAlpha: true, antialias: true })
  if (!gl) return null
  const compile = (type: number, source: string) => {
    const shader = gl.createShader(type) as WebGLShader
    gl.shaderSource(shader, source)
    gl.compileShader(shader)
    return shader
  }
  const program = gl.createProgram()
  gl.attachShader(program, compile(gl.VERTEX_SHADER, VERTEX))
  gl.attachShader(program, compile(gl.FRAGMENT_SHADER, FRAGMENT))
  gl.linkProgram(program)
  if (!gl.getProgramParameter(program, gl.LINK_STATUS)) return null
  gl.useProgram(program)
  gl.bindBuffer(gl.ARRAY_BUFFER, gl.createBuffer())
  gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([-1, -1, 3, -1, -1, 3]), gl.STATIC_DRAW)
  const position = gl.getAttribLocation(program, 'p')
  gl.enableVertexAttribArray(position)
  gl.vertexAttribPointer(position, 2, gl.FLOAT, false, 0, 0)
  const resolution = gl.getUniformLocation(program, 'r')
  const time = gl.getUniformLocation(program, 't')
  const amplitude = gl.getUniformLocation(program, 'a')
  const thinking = gl.getUniformLocation(program, 'm')
  return (t, level, think) => {
    gl.viewport(0, 0, canvas.width, canvas.height)
    gl.clearColor(0, 0, 0, 0)
    gl.clear(gl.COLOR_BUFFER_BIT)
    gl.uniform2f(resolution, canvas.width, canvas.height)
    gl.uniform1f(time, t)
    gl.uniform1f(amplitude, level)
    gl.uniform1f(thinking, think)
    gl.drawArrays(gl.TRIANGLES, 0, 3)
  }
}
