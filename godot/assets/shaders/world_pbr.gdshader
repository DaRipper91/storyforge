shader_type spatial;
// Triplanar PBR for props, walls, rocks and house parts (world-space mapping, so a MultiMesh of
// one mesh and a scaled box both get the same texel density). Mobile-renderer safe: 2 texture
// fetches per projection (albedo + packed normal/roughness), no screen reads, no discard.
// Texture packing: *_alb = albedo, *_nrm_rgh = RGB tangent-space normal (GL), A = roughness.
render_mode cull_back, diffuse_burley, specular_schlick_ggx;

uniform sampler2D albedo_tex : source_color, filter_linear_mipmap, repeat_enable;
uniform sampler2D nrm_rgh_tex : filter_linear_mipmap, repeat_enable;
uniform vec4 tint : source_color = vec4(1.0);
uniform float tile_metres = 2.0;       // world metres covered by one texture tile
uniform float normal_strength = 1.0;
uniform float roughness_mul = 1.0;
uniform float blend_sharpness = 4.0;
uniform float macro_amount = 0.22;     // low-frequency brightness variation that hides tiling
uniform float vertex_color_mix = 1.0;  // 0 = ignore COLOR, 1 = multiply albedo by COLOR.rgb
uniform float emission_amount = 0.0;
uniform vec4 emission_color : source_color = vec4(1.0, 0.7, 0.35, 1.0);
uniform float night_glow = 0.0;        // driven by WorldAtmosphere: windows/lanterns light up after dusk
uniform float rotate_x_planks = 0.0;   // 1 = turn the side projections 90 degrees (vertical planks)

varying vec3 v_pos;
varying vec3 v_nrm;
varying vec4 v_col;

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
	v_pos = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
	v_nrm = normalize((MODEL_MATRIX * vec4(NORMAL, 0.0)).xyz);
	v_col = COLOR;
}

void fragment() {
	vec3 n = normalize(v_nrm);
	vec3 w = pow(abs(n), vec3(blend_sharpness));
	w /= (w.x + w.y + w.z);
	float k = 1.0 / tile_metres;
	vec2 uvx = v_pos.zy * k;
	vec2 uvy = v_pos.xz * k;
	vec2 uvz = v_pos.xy * k;
	if (rotate_x_planks > 0.5) {
		uvx = uvx.yx;
		uvz = uvz.yx;
	}
	vec3 cx = texture(albedo_tex, uvx).rgb;
	vec3 cy = texture(albedo_tex, uvy).rgb;
	vec3 cz = texture(albedo_tex, uvz).rgb;
	vec3 alb = cx * w.x + cy * w.y + cz * w.z;

	vec4 nx = texture(nrm_rgh_tex, uvx);
	vec4 ny = texture(nrm_rgh_tex, uvy);
	vec4 nz = texture(nrm_rgh_tex, uvz);
	float rough = (nx.a * w.x + ny.a * w.y + nz.a * w.z) * roughness_mul;
	// Whiteout blend of the three tangent-space normals into a world-space normal.
	vec3 tx = (nx.rgb * 2.0 - 1.0) * vec3(normal_strength, normal_strength, 1.0);
	vec3 ty = (ny.rgb * 2.0 - 1.0) * vec3(normal_strength, normal_strength, 1.0);
	vec3 tz = (nz.rgb * 2.0 - 1.0) * vec3(normal_strength, normal_strength, 1.0);
	tx = vec3(tx.xy + n.zy, abs(tx.z) * n.x);
	ty = vec3(ty.xy + n.xz, abs(ty.z) * n.y);
	tz = vec3(tz.xy + n.xy, abs(tz.z) * n.z);
	vec3 wn = normalize(tx.zyx * w.x + ty.xzy * w.y + tz.xyz * w.z);
	NORMAL = (VIEW_MATRIX * vec4(wn, 0.0)).xyz;

	float macro = vnoise(v_pos.xz * 0.21 + v_pos.y * 0.37) * 0.6 + vnoise(v_pos.xz * 0.9) * 0.4;
	alb *= 1.0 - macro_amount + macro * macro_amount * 2.0;
	alb *= tint.rgb * mix(vec3(1.0), v_col.rgb, vertex_color_mix);
	ALBEDO = alb;
	ROUGHNESS = clamp(rough, 0.05, 1.0);
	METALLIC = 0.0;
	EMISSION = emission_color.rgb * (emission_amount + night_glow) * v_col.a;
}
