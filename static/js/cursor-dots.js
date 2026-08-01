/**
 * Cursor Dots — WebGL Background Shader
 * Pure white (#FFFFFF) in light mode, dark (#191918) in dark mode.
 * Small dots appear around the cursor. Subtle, precise, premium.
 */
(function () {
    const canvas = document.createElement('canvas');
    canvas.style.cssText = 'position:fixed;inset:0;z-index:0;pointer-events:none;';
    document.body.prepend(canvas);

    let cursorX = -9999;
    let cursorY = -9999;
    let targetX = -9999;
    let targetY = -9999;
    let firstMove = true;

    document.addEventListener('mousemove', function (e) {
        targetX = e.clientX;
        targetY = e.clientY;
    });

    document.addEventListener('mouseleave', function () {
        targetX = -9999;
        targetY = -9999;
    });

    // Load Three.js dynamically
    function init(THREE) {
        const renderer = new THREE.WebGLRenderer({ canvas, alpha: false, antialias: true });
        renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
        renderer.setSize(window.innerWidth, window.innerHeight);

        const scene = new THREE.Scene();
        const camera = new THREE.OrthographicCamera(-1, 1, 1, -1, 0, 1);

        const uniforms = {
            u_time: { value: 0 },
            u_resolution: { value: new THREE.Vector2(window.innerWidth, window.innerHeight) },
            u_cursor: { value: new THREE.Vector2(-9999, -9999) },
            u_dark: { value: document.documentElement.getAttribute('data-theme') === 'dark' ? 1.0 : 0.0 },
            u_oled: { value: document.documentElement.hasAttribute('data-oled') ? 1.0 : 0.0 },
        };

        const material = new THREE.ShaderMaterial({
            vertexShader: /* glsl */ `
                precision highp float;
                varying vec2 v_uv;
                void main() {
                    gl_Position = vec4(position.xy, 0.0, 1.0);
                    v_uv = position.xy * 0.5 + 0.5;
                }
            `,
            fragmentShader: /* glsl */ `
                precision highp float;
                varying vec2 v_uv;

                uniform float u_time;
                uniform vec2 u_resolution;
                uniform vec2 u_cursor;
                uniform float u_dark;
                uniform float u_oled;

                void main() {
                    // Convert UV to pixel coords
                    vec2 px = v_uv * u_resolution;

                    // Distance from cursor in pixels
                    float dist = distance(px, u_cursor);

                    // Influence radius — dots only appear within this area
                    float radius = 160.0;

                    // Smooth radial falloff (0 at center, 1 at edge) — inverted: 1 near cursor, 0 at edge
                    float influence = 1.0 - smoothstep(0.0, radius, dist);

                    // Grid spacing
                    float gridSize = 10.0;

                    // Snap to nearest grid intersection
                    vec2 gridCoord = floor(px / gridSize + 0.5) * gridSize;
                    float distToGrid = distance(px, gridCoord);

                    // Dot size — tiny pulsation
                    float dotRadius = 1.8 * (1.0 + sin(u_time * 2.5) * 0.06);
                    float dot = 1.0 - smoothstep(0.0, dotRadius, distToGrid);

                    // Combine: dot visibility × cursor proximity influence
                    float alpha = dot * influence;

                    // Light mode: white bg, black dots. Dark mode: dark bg, light dots.
                    vec3 bgLight  = vec3(1.0, 1.0, 1.0);
                    vec3 dotLight = vec3(0.0, 0.0, 0.0);
                    vec3 bgDark   = vec3(0.098, 0.098, 0.094); // #191918
                    vec3 bgOled   = vec3(0.0, 0.0, 0.0);       // #000000 (OLED)
                    vec3 dotDark  = vec3(0.945, 0.945, 0.937); // #f1f1ef

                    vec3 bg  = mix(mix(bgLight, bgDark, u_dark), bgOled, u_oled);
                    vec3 dotClr = mix(dotLight, dotDark, u_dark);
                    vec3 color = mix(bg, dotClr, alpha * 0.55);

                    gl_FragColor = vec4(color, 1.0);
                }
            `,
            uniforms: uniforms,
        });

        const geometry = new THREE.PlaneGeometry(2, 2);
        const mesh = new THREE.Mesh(geometry, material);
        scene.add(mesh);

        function animate() {
            requestAnimationFrame(animate);

            // Skip lerp on first move or large jumps — snap immediately
            if (firstMove || Math.abs(targetX - cursorX) > 500) {
                cursorX = targetX;
                cursorY = targetY;
                firstMove = false;
            } else {
                cursorX += (targetX - cursorX) * 0.12;
                cursorY += (targetY - cursorY) * 0.12;
            }

            // Flip Y because WebGL Y is inverted vs DOM
            uniforms.u_cursor.value.set(cursorX, window.innerHeight - cursorY);
            uniforms.u_time.value += 0.016;
            renderer.render(scene, camera);
        }
        animate();

        window.addEventListener('resize', function () {
            renderer.setSize(window.innerWidth, window.innerHeight);
            uniforms.u_resolution.value.set(window.innerWidth, window.innerHeight);
        });

        // Listen for theme changes
        window.addEventListener('themechange', function (e) {
            var t = e.detail.theme;
            uniforms.u_dark.value = (t === 'dark' || t === 'oled') ? 1.0 : 0.0;
            uniforms.u_oled.value = t === 'oled' ? 1.0 : 0.0;
        });
    }

    if (window.THREE) {
        init(window.THREE);
    } else {
        var script = document.createElement('script');
        script.src = 'https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js';
        script.crossOrigin = 'anonymous';
        script.async = true;
        script.onload = function () {
            if (window.THREE) init(window.THREE);
        };
        document.head.appendChild(script);
    }
})();
