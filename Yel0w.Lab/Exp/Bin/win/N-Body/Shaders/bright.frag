#version 330 core

in vec2 vTexCoord;
out vec4 FragColor;

uniform sampler2D uScene;
uniform float uThreshold;

void main() {
    vec3 color = texture(uScene, vTexCoord).rgb;
    float brightness = dot(color, vec3(0.2126, 0.7152, 0.0722));
    float contribution = max(brightness - uThreshold, 0.0);
    FragColor = vec4(contribution * color / max(brightness, 0.001), 1.0);
}
