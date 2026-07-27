#version 330 core

in vec3 vNormal;
in vec3 vFragPos;
in vec3 vLocalPos;
in float vMass;
in float vColorSeed;

out vec4 FragColor;

uniform vec3 uViewPos;

vec3 starColor(float t) {
    vec3 red    = vec3(1.0, 0.25, 0.05);
    vec3 orange = vec3(1.0, 0.6,  0.1);
    vec3 yellow = vec3(1.0, 0.95, 0.7);
    vec3 white  = vec3(1.0, 1.0,  1.0);
    vec3 blue   = vec3(0.6, 0.7,  1.0);

    if (t < 0.25) return mix(red, orange, t / 0.25);
    if (t < 0.5)  return mix(orange, yellow, (t - 0.25) / 0.25);
    if (t < 0.75) return mix(yellow, white, (t - 0.5) / 0.25);
    return mix(white, blue, (t - 0.75) / 0.25);
}

float hash(vec3 p) {
    p = fract(p * 0.3183099 + 0.1);
    p *= 17.0;
    return fract(p.x * p.y * p.z * (p.x + p.y + p.z));
}

float noise(vec3 p) {
    vec3 i = floor(p);
    vec3 f = fract(p);
    f = f * f * (3.0 - 2.0 * f);
    return mix(
        mix(mix(hash(i), hash(i + vec3(1,0,0)), f.x),
            mix(hash(i + vec3(0,1,0)), hash(i + vec3(1,1,0)), f.x), f.y),
        mix(mix(hash(i + vec3(0,0,1)), hash(i + vec3(1,0,1)), f.x),
            mix(hash(i + vec3(0,1,1)), hash(i + vec3(1,1,1)), f.x), f.y), f.z);
}

void main() {
    float mass = clamp(vMass, 0.0, 1.0);

    vec3 normal = normalize(vNormal);
    vec3 viewDir = normalize(uViewPos - vFragPos);
    vec3 lightDir = normalize(-vFragPos);

    float fresnel = pow(1.0 - max(dot(normal, viewDir), 0.0), 3.0);

    float n = noise(vLocalPos * 6.0 + vColorSeed * 100.0);
    float n2 = noise(vLocalPos * 12.0 + vColorSeed * 100.0 + 50.0);
    float detail = n * 0.7 + n2 * 0.3;

    float t = clamp(mass + (vColorSeed - 0.5) * 0.08, 0.0, 1.0);
    vec3 hot  = starColor(t);
    vec3 cool = starColor(t) * vec3(0.6, 0.3, 0.15);
    vec3 baseColor = mix(hot, cool, detail * 0.4);

    float diff = max(dot(normal, lightDir), 0.0);
    vec3 halfwayDir = normalize(lightDir + viewDir);
    float spec = pow(max(dot(normal, halfwayDir), 0.0), 128.0);

    float ambient = 0.02;
    float diffuse = mix(0.15, 0.85, diff);
    float specular = mix(0.0, 0.4, mass) * spec;

    float emissive = mix(0.4, 2.0, mass);
    float rimPower = mix(1.5, 4.0, mass);
    float rim = pow(1.0 - max(dot(normal, viewDir), 0.0), rimPower);
    vec3 rimColor = mix(hot, vec3(1.0), 0.5) * rim * mix(0.3, 1.2, mass);

    vec3 color = baseColor * (ambient + diffuse) + vec3(specular) * mix(0.3, 1.0, mass);
    color += baseColor * emissive;
    color += rimColor;

    float brightness = mix(0.6, 2.5, mass);
    FragColor = vec4(color * brightness, 1.0);
}
