shader_type spatial;
// Ground: grass (ground037) blended into cobble (paving) along path segments and plaza circles,
// with noisy edges, plus a distance fade into the horizon/fog colour so the edge of the world is
// never visible. Planar world-XZ mapping (the ground is flat): 4 texture fetches total.
render_mode cull_back, diffuse_burley;

uniform sampler2D grass_alb : source_color, filter_linear_mipmap, repeat_enable;
uniform sampler2D grass_nrm : filter_linear_mipmap, repeat_enable;
uniform sampler2D path_alb : source_color, filter_linear_mipmap, repeat_enable;
uniform sampler2D path_nrm : filter_linear_mipmap, repeat_enable;
uniform vec4 grass_tint : source_color = vec4(0.85, 0.95, 0.7, 1.0);
uniform vec4 path_tint : source_color = vec4(1.0);
uniform float grass_tile = 3.0;
uniform float path_tile = 2.2;
// up to 8 path segments (a.xz, b.xz) with half widths, up to 4 plaza circles (x, z, radius)
uniform vec4 segs[8];
uniform float seg_half_width[8];
uniform vec3 circles[4];
uniform vec4 base_tint_far : source_color = vec4(0.7, 0.8, 0.6, 1.0);
uniform vec2 fade_center = vec2(10.0, 10.0);
uniform float fade_start = 40.0;
uniform float fade_end = 95.0;
uniform vec4 fade_color : source_color = vec4(0.55, 0.65, 0.75, 1.0);
uniform float normal_strength = 1.0;

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
float seg_dist(vec2 p, vec2 a, vec2 b) {
	vec2 pa = p - a;
	vec2 ba = b - a;
	float h = clamp(dot(pa, ba) / max(dot(ba, ba), 0.0001), 0.0, 1.0);
	return length(pa - ba * h);
}

void vertex() {
	v_pos = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
}

void fragment() {
	vec2 p = v_pos.xz;
	// signed "inside path" value: > 0 on the path
	float inside = -100.0;
	for (int i = 0; i < 8; i++) {
		if (seg_half_width[i] > 0.0) {
			inside = max(inside, seg_half_width[i] - seg_dist(p, segs[i].xy, segs[i].zw));
		}
	}
	for (int j = 0; j < 4; j++) {
		if (circles[j].z > 0.0) {
			inside = max(inside, circles[j].z - length(p - circles[j].xy));
		}
	}
	float edge_noise = (vnoise(p * 2.3) - 0.5) * 0.55 + (vnoise(p * 7.1) - 0.5) * 0.18;
	float m = smoothstep(-0.12, 0.12, inside + edge_noise);   // 1 = cobble
	// a dirt-worn fringe just outside the cobble: darken and desaturate the grass
	float fringe = smoothstep(-0.9, 0.0, inside + edge_noise) * (1.0 - m);

	vec2 guv = p / grass_tile;
	vec2 puv = p / path_tile;
	vec3 ga = texture(grass_alb, guv).rgb * grass_tint.rgb;
	vec3 pa = texture(path_alb, puv).rgb * path_tint.rgb;
	ga = mix(ga, ga * vec3(0.78, 0.66, 0.5), fringe * 0.8);
	float macro = vnoise(p * 0.18) * 0.6 + vnoise(p * 0.7) * 0.4;
	ga *= 0.8 + macro * 0.5;
	vec3 alb = mix(ga, pa, m);
	vec4 gn = texture(grass_nrm, guv);
	vec4 pn = texture(path_nrm, puv);
	vec4 nn = mix(gn, pn, m);
	vec3 tn = vec3((nn.rg * 2.0 - 1.0) * normal_strength, 1.0);
	tn = normalize(tn);
	// world-up surface: tangent x = world +X, tangent y = world -Z (GL normal map on an XZ plane)
	vec3 wn = normalize(vec3(tn.x, tn.z, -tn.y));
	NORMAL = (VIEW_MATRIX * vec4(wn, 0.0)).xyz;
	ROUGHNESS = clamp(nn.a, 0.1, 1.0);
	float d = length(p - fade_center);
	float f = smoothstep(fade_start, fade_end, d);
	ALBEDO = mix(alb, fade_color.rgb, f);
	ROUGHNESS = mix(ROUGHNESS, 1.0, f);
}
