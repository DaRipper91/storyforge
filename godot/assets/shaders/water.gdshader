shader_type spatial;
// Cheap pool/fountain water: two scrolling procedural ripple normals, depth-free colour,
// fresnel sky tint, specular glint. No screen texture or depth texture (Mobile safe).
render_mode cull_back, specular_schlick_ggx;

uniform vec4 shallow_color : source_color = vec4(0.18, 0.42, 0.5, 1.0);
uniform vec4 deep_color : source_color = vec4(0.05, 0.16, 0.24, 1.0);
uniform vec4 sky_tint : source_color = vec4(0.6, 0.75, 0.9, 1.0);
uniform float ripple_scale = 3.0;
uniform float ripple_speed = 0.35;
uniform float ripple_strength = 0.35;
uniform vec2 centre = vec2(0.0);
uniform float radius = 1.0;

varying vec3 v_local;

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
	v_local = VERTEX;
}

void fragment() {
	vec2 p = v_local.xz * ripple_scale;
	float t = TIME * ripple_speed;
	float a = vnoise(p + vec2(t, t * 0.6));
	float b = vnoise(p * 1.9 - vec2(t * 0.8, t));
	vec2 g = vec2(a - 0.5, b - 0.5) * ripple_strength;
	vec3 n = normalize(vec3(g.x, 1.0, g.y));
	NORMAL = (VIEW_MATRIX * vec4(n, 0.0)).xyz;
	float r = clamp(length(v_local.xz) / max(radius, 0.01), 0.0, 1.0);
	vec3 col = mix(shallow_color.rgb, deep_color.rgb, smoothstep(0.7, 0.0, r));
	float fres = pow(1.0 - clamp(dot(normalize(NORMAL), normalize(VIEW)), 0.0, 1.0), 3.0);
	ALBEDO = mix(col, sky_tint.rgb, fres * 0.6);
	ROUGHNESS = 0.06;
	SPECULAR = 0.9;
	METALLIC = 0.0;
}
