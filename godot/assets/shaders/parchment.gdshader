shader_type spatial;
render_mode blend_mix, depth_draw_opaque, cull_back, diffuse_burley, specular_schlick_ggx;

// Core parchment color
uniform vec4 base_color : source_color = vec4(0.92, 0.87, 0.78, 1.0);
uniform vec4 ink_color : source_color = vec4(0.15, 0.12, 0.15, 1.0);

// Texture for the paper fibers / noise
uniform sampler2D noise_texture;

// Roughness for paper
uniform float roughness : hint_range(0.0, 1.0) = 0.95;

void fragment() {
    // Sample the noise to create variation in the paper
    vec2 uv = UV * 3.0; // Scale the noise
    float noise_val = texture(noise_texture, uv).r;
    
    // Mix the base color with a slightly darker variant based on noise
    vec3 final_color = mix(base_color.rgb * 0.85, base_color.rgb, noise_val);
    
    ALBEDO = final_color;
    ROUGHNESS = roughness;
    SPECULAR = 0.1;
}
