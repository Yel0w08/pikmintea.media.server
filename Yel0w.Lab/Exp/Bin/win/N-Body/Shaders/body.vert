#version 330 core

layout(location = 0) in vec3 aPos;
layout(location = 1) in vec3 iPosition;
layout(location = 2) in float iScale;
layout(location = 3) in float iMass;
layout(location = 4) in float iColorSeed;

uniform mat4 uView;
uniform mat4 uProjection;

out vec3 vNormal;
out vec3 vFragPos;
out vec3 vLocalPos;
out float vMass;
out float vColorSeed;

void main() {
    vec3 worldPos = aPos * iScale + iPosition;
    gl_Position = uProjection * uView * vec4(worldPos, 1.0);
    vNormal = normalize(aPos);
    vFragPos = worldPos;
    vLocalPos = aPos;
    vMass = iMass;
    vColorSeed = iColorSeed;
}
