#version 330 core

in vec2 vTexCoord;
out vec4 FragColor;

uniform sampler2D uTexture;
uniform float uHorizontal;
uniform vec2 uTexelSize;

void main() {
    vec3 result = texture(uTexture, vTexCoord).rgb * 0.227027;

    if (uHorizontal > 0.5) {
        result += texture(uTexture, vTexCoord + vec2(uTexelSize.x * 1.0, 0.0)).rgb * 0.1945946;
        result += texture(uTexture, vTexCoord - vec2(uTexelSize.x * 1.0, 0.0)).rgb * 0.1945946;
        result += texture(uTexture, vTexCoord + vec2(uTexelSize.x * 2.0, 0.0)).rgb * 0.1216216;
        result += texture(uTexture, vTexCoord - vec2(uTexelSize.x * 2.0, 0.0)).rgb * 0.1216216;
        result += texture(uTexture, vTexCoord + vec2(uTexelSize.x * 3.0, 0.0)).rgb * 0.054054;
        result += texture(uTexture, vTexCoord - vec2(uTexelSize.x * 3.0, 0.0)).rgb * 0.054054;
        result += texture(uTexture, vTexCoord + vec2(uTexelSize.x * 4.0, 0.0)).rgb * 0.016216;
        result += texture(uTexture, vTexCoord - vec2(uTexelSize.x * 4.0, 0.0)).rgb * 0.016216;
    } else {
        result += texture(uTexture, vTexCoord + vec2(0.0, uTexelSize.y * 1.0)).rgb * 0.1945946;
        result += texture(uTexture, vTexCoord - vec2(0.0, uTexelSize.y * 1.0)).rgb * 0.1945946;
        result += texture(uTexture, vTexCoord + vec2(0.0, uTexelSize.y * 2.0)).rgb * 0.1216216;
        result += texture(uTexture, vTexCoord - vec2(0.0, uTexelSize.y * 2.0)).rgb * 0.1216216;
        result += texture(uTexture, vTexCoord + vec2(0.0, uTexelSize.y * 3.0)).rgb * 0.054054;
        result += texture(uTexture, vTexCoord - vec2(0.0, uTexelSize.y * 3.0)).rgb * 0.054054;
        result += texture(uTexture, vTexCoord + vec2(0.0, uTexelSize.y * 4.0)).rgb * 0.016216;
        result += texture(uTexture, vTexCoord - vec2(0.0, uTexelSize.y * 4.0)).rgb * 0.016216;
    }

    FragColor = vec4(result, 1.0);
}
