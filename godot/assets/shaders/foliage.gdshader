shader_type spatial;
// Tree crowns and bushes: vertex-colour albedo (leaf clusters), a touch of world noise, and a
// cheap wind sway in the vertex stage (no textures, no per-frame CPU work). Works per-instance
// inside a MultiMeshInstance3D.
render_mode cull_back, diffuse_burley;

uniform vec4 tint : source_color = vec4(1.0);
uniform float wind_strength = 0.06;
uniform float wind_speed = 1.4;
uniform float sway_height = 6.0;      // height at which sway reaches full strength
uniform float night_dim = 0.0;
varying vec3 v_pos;

float hash21(vec2 p) {
	p = fract(p * vec2(123.34, 456.21));
	p += dot(p, p + 45.32);
	return fract(p.x * p.y);
}
float vnoise(vec2 p) {
	vec2 i = floor(p);
	vec2 f = fract(p);
	f = f * f * (3.0 - 2.0 * f);
	return mix(mix(hash21(i), hash21(i + vec2(1.0, 0.0)), f.x),
		mix(hash21(i + vec2(0.0, 1.0)), hash21(i + vec2(1.0, 1.0)), f.x), f.y);
}

void vertex() {
	vec3 wp = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
	float h = clamp(VERTEX.y / sway_height, 0.0, 1.0);
	float ph = wp.x * 0.35 + wp.z * 0.27;
	float t = TIME * wind_speed;
	vec3 sway = vec3(sin(t + ph) + 0.5 * sin(t * 2.3 + ph * 1.7), 0.0, cos(t * 0.8 + ph)) * wind_strength * h * h;
	VERTEX += (inverse(mat3(MODEL_MATRIX)) * sway);
	v_pos = wp;
}

void fragment() {
	float n = vnoise(v_pos.xz * 1.7 + v_pos.y * 0.9);
	vec3 c = COLOR.rgb * tint.rgb * (0.82 + n * 0.36);
	ALBEDO = c;
	ROUGHNESS = 0.85;
	// a faint translucent rim so the crowns glow where the sun grazes them
	RIM = 0.15;
	RIM_TINT = 0.6;
}
