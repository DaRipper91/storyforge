shader_type spatial;
render_mode depth_draw_opaque, cull_disabled;

uniform sampler2D albedo_texture : source_color, filter_nearest;
uniform vec4 outline_color : source_color = vec4(0.0, 1.0, 0.8, 1.0);
uniform float outline_width : hint_range(0.0, 10.0) = 2.0;
uniform float alpha_threshold : hint_range(0.0, 1.0) = 0.5;
uniform float glow_intensity : hint_range(0.0, 10.0) = 2.0;
uniform float flash_ratio : hint_range(0.0, 1.0) = 0.0;

void fragment() {
    vec4 col = texture(albedo_texture, UV);
    
    // Check neighbors to detect outline
    vec2 size = vec2(textureSize(albedo_texture, 0));
    float alpha = col.a;
    
    float max_alpha = 0.0;
    if (alpha < alpha_threshold) {
        // Sample neighbors
        float step_x = outline_width / size.x;
        float step_y = outline_width / size.y;
        
        for (float x = -1.0; x <= 1.0; x += 1.0) {
            for (float y = -1.0; y <= 1.0; y += 1.0) {
                if (x == 0.0 && y == 0.0) continue;
                vec2 n_uv = UV + vec2(x * step_x, y * step_y);
                if (n_uv.x >= 0.0 && n_uv.x <= 1.0 && n_uv.y >= 0.0 && n_uv.y <= 1.0) {
                    max_alpha = max(max_alpha, texture(albedo_texture, n_uv).a);
                }
            }
        }
    }
    
    if (alpha >= alpha_threshold) {
        vec3 final_color = mix(col.rgb, vec3(1.0, 0.0, 0.0), flash_ratio);
        ALBEDO = final_color;
        ALPHA = 1.0;
        if (flash_ratio > 0.01) {
            EMISSION = vec3(1.0, 0.0, 0.0) * flash_ratio * 4.0;
        }
    } else if (max_alpha >= alpha_threshold) {
        ALBEDO = outline_color.rgb;
        ALPHA = 1.0;
        EMISSION = outline_color.rgb * glow_intensity;
    } else {
        discard;
    }
}
