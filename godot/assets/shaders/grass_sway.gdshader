shader_type spatial;
// Grass tufts / flowers on a MultiMesh. Each instance is a few crossed blade quads; COLOR.a is
// the height weight (0 at the root, 1 at the tip) so only the tips sway. No textures, no discard:
// blades are real triangles (a few per tuft), so this is cheap on Mobile.
render_mode cull_disabled, diffuse_burley;

uniform vec4 root_color : source_color = vec4(0.12, 0.22, 0.07, 1.0);
uniform vec4 tip_color : source_color = vec4(0.55, 0.68, 0.25, 1.0);
uniform float wind_strength = 0.12;
uniform float wind_speed = 1.7;
uniform float use_vertex_color = 0.0;  // 1 for flowers: COLOR.rgb is the petal/stem colour

varying float v_h;

void vertex() {
	vec3 wp = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
	float h = COLOR.a;
	float t = TIME * wind_speed;
	float ph = wp.x * 0.6 + wp.z * 0.45;
	vec3 sway = vec3(sin(t + ph), 0.0, cos(t * 0.9 + ph * 1.3)) * wind_strength * h * h;
	VERTEX += inverse(mat3(MODEL_MATRIX)) * sway;
	v_h = h;
}

void fragment() {
	vec3 g = mix(root_color.rgb, tip_color.rgb, v_h);
	ALBEDO = mix(g, COLOR.rgb, use_vertex_color * step(0.5, v_h));
	ROUGHNESS = 0.9;
}
