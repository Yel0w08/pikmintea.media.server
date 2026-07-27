#version 330 core

in vec2 vTexCoord;
out vec4 FragColor;

uniform sampler2D uScene;
uniform sampler2D uBloom;
uniform float uBloomIntensity;

void main() {
    vec3 sceneColor = texture(uScene, vTexCoord).rgb;
    vec3 bloomColor = texture(uBloom, vTexCoord).rgb;
    FragColor = vec4(sceneColor + bloomColor * uBloomIntensity, 1.0);
}
