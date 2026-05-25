shader_type spatial;
render_mode blend_mix, depth_draw_opaque, cull_back, diffuse_burley, specular_schlick_ggx;

uniform vec4 albedo : source_color = vec4(1.0);
uniform float metallic : hint_range(0.0, 1.0) = 0.2;
uniform float roughness : hint_range(0.0, 1.0) = 0.5;

uniform vec4 rim_color : source_color = vec4(1.0);
uniform float rim_power : hint_range(0.0, 10.0) = 2.0;
uniform float rim_intensity : hint_range(0.0, 5.0) = 1.0;

void fragment() {
	ALBEDO = albedo.rgb;
	METALLIC = metallic;
	ROUGHNESS = roughness;
	
	// Rim lighting calculation
	float NdotV = dot(NORMAL, VIEW);
	float rim = 1.0 - clamp(NdotV, 0.0, 1.0);
	rim = smoothstep(0.0, 1.0, rim);
	rim = pow(rim, rim_power);
	
	EMISSION = rim_color.rgb * rim * rim_intensity;
}