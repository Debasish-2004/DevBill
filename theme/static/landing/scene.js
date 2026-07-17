/* ═══════════════════════════════════════════════════════════════
   DEVBILL · scene.js
   Builds the Three.js world and exposes it on window.DEVBILL so
   animations.js / interactions.js can drive it.

   Performance notes
   ─────────────────
   • Everything is low-poly primitives — no model loading.
   • Text / barcode / QR / receipt are tiny <canvas> textures,
     drawn once at startup (zero per-frame cost).
   • One shared wireframe material per colour, geometries reused.
   • No shadows, no post-processing, no physics.
   ═══════════════════════════════════════════════════════════════ */

(function () {
    'use strict';

    const COL = {
        bg: 0x04060D,
        blue: 0x3B82F6,
        purple: 0x8B5CF6,
        cyan: 0x22D3EE,
        white: 0xEAF2FF,
    };

    /* ── Renderer / scene / camera ──────────────────────────── */

    const canvas = document.getElementById('scene-canvas');
    const renderer = new THREE.WebGLRenderer({
        canvas,
        antialias: true,
        alpha: true,               // aurora CSS shows through
        powerPreference: 'low-power',
    });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 1.75));
    renderer.setSize(window.innerWidth, window.innerHeight);

    const scene = new THREE.Scene();
    scene.fog = new THREE.Fog(COL.bg, 18, 46);   // grid melts into darkness

    const camera = new THREE.PerspectiveCamera(
        50, window.innerWidth / window.innerHeight, 0.1, 100
    );
    camera.position.set(0, 2.1, 11);

    /* ── Lighting: soft ambient + blue/purple edge lights ────── */

    scene.add(new THREE.AmbientLight(0x2A3550, 1.1));

    const keyLight = new THREE.DirectionalLight(COL.blue, 0.55);
    keyLight.position.set(6, 8, 6);
    scene.add(keyLight);

    const rimLight = new THREE.DirectionalLight(COL.purple, 0.35);
    rimLight.position.set(-7, 4, -5);
    scene.add(rimLight);

    const fillLight = new THREE.PointLight(COL.cyan, 0.5, 24);
    fillLight.position.set(0, 3, 4);
    scene.add(fillLight);

    /* ── Helpers ─────────────────────────────────────────────── */

    /** Canvas-texture factory: draw once, use forever. */
    function makeCanvasTexture(w, h, draw) {
        const cv = document.createElement('canvas');
        cv.width = w; cv.height = h;
        draw(cv.getContext('2d'), w, h);
        const tex = new THREE.CanvasTexture(cv);
        tex.anisotropy = 2;
        return tex;
    }

    function wireMat(color, opacity) {
        return new THREE.MeshBasicMaterial({
            color, wireframe: true, transparent: true, opacity,
        });
    }

    /* Group that gently floats: each entry gets phase/speed/amp
       used by animations.js for the zero-gravity drift. */
    const floaters = [];
    function float(obj, amp, speed, rotSpeed) {
        floaters.push({
            obj,
            baseY: obj.position.y,
            amp: amp ?? 0.25,
            speed: speed ?? 0.4,
            rot: rotSpeed ?? 0.12,
            phase: Math.random() * Math.PI * 2,
        });
    }

    /* ── Infinite wireframe grid (fades into fog) ────────────── */

    const grid = new THREE.GridHelper(90, 60, COL.blue, 0x12203C);
    grid.material.transparent = true;
    grid.material.opacity = 0.34;
    grid.position.y = -1.6;
    scene.add(grid);

    /* ── Tiny low-poly grocery shop ──────────────────────────── */

    const store = new THREE.Group();

    // walls
    const storeBody = new THREE.Mesh(
        new THREE.BoxGeometry(3.4, 1.9, 2.4),
        new THREE.MeshStandardMaterial({
            color: 0x0B1428, roughness: 0.55, metalness: 0.35,
            emissive: 0x0A1A38, emissiveIntensity: 0.7,
        })
    );
    storeBody.position.y = 0.95;
    store.add(storeBody);

    // wireframe overlay for the neon-blueprint feel
    const storeWire = new THREE.Mesh(
        new THREE.BoxGeometry(3.42, 1.92, 2.42), wireMat(COL.blue, 0.28)
    );
    storeWire.position.y = 0.95;
    store.add(storeWire);

    // roof
    const roof = new THREE.Mesh(
        new THREE.ConeGeometry(2.65, 1.05, 4),
        new THREE.MeshStandardMaterial({
            color: 0x101E3E, roughness: 0.5, metalness: 0.3,
            emissive: 0x14265A, emissiveIntensity: 0.6,
        })
    );
    roof.rotation.y = Math.PI / 4;
    roof.position.y = 2.42;
    store.add(roof);

    // glowing awning strip
    const awning = new THREE.Mesh(
        new THREE.BoxGeometry(3.5, 0.1, 0.55),
        new THREE.MeshBasicMaterial({ color: COL.cyan, transparent: true, opacity: 0.85 })
    );
    awning.position.set(0, 1.62, 1.35);
    store.add(awning);

    // doorway (emissive portal — the camera flies into this on enter)
    const door = new THREE.Mesh(
        new THREE.PlaneGeometry(0.85, 1.25),
        new THREE.MeshBasicMaterial({ color: 0x9BC4FF, transparent: true, opacity: 0.9 })
    );
    door.position.set(0, 0.63, 1.21);
    store.add(door);

    // "DEVBILL MART" signboard
    const signTex = makeCanvasTexture(512, 128, (ctx, w, h) => {
        ctx.fillStyle = 'rgba(8,14,30,0.9)';
        ctx.fillRect(0, 0, w, h);
        ctx.font = '700 58px system-ui, sans-serif';
        ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
        ctx.shadowColor = '#3B82F6'; ctx.shadowBlur = 26;
        ctx.fillStyle = '#CFE4FF';
        ctx.fillText('LINGARAJ SANITARY', w / 2, h / 2 + 3);
    });
    const sign = new THREE.Mesh(
        new THREE.PlaneGeometry(2.5, 0.62),
        new THREE.MeshBasicMaterial({ map: signTex, transparent: true })
    );
    sign.position.set(0, 2.0, 1.22);
    store.add(sign);

    store.position.set(0, -1.55, -3.2);
    scene.add(store);
    float(store, 0.10, 0.22, 0);

    /* ── Futuristic product boxes ────────────────────────────── */

    function productTexture(label, hex) {
        return makeCanvasTexture(256, 256, (ctx, w, h) => {
            ctx.fillStyle = '#080F22';
            ctx.fillRect(0, 0, w, h);
            // frame
            ctx.strokeStyle = hex; ctx.lineWidth = 5;
            ctx.strokeRect(12, 12, w - 24, h - 24);
            // corner ticks
            ctx.fillStyle = hex;
            [[24, 24], [w - 40, 24], [24, h - 40], [w - 40, h - 40]]
                .forEach(([x, y]) => ctx.fillRect(x, y, 16, 16));
            // label
            ctx.font = '700 44px system-ui, sans-serif';
            ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
            ctx.shadowColor = hex; ctx.shadowBlur = 18;
            ctx.fillStyle = '#E4EEFF';
            ctx.fillText(label, w / 2, h / 2);
            // tiny fake barcode footer
            ctx.shadowBlur = 0;
            for (let x = 70; x < 190; x += 6) {
                ctx.fillStyle = 'rgba(160,190,240,0.65)';
                ctx.fillRect(x, h - 46, Math.random() > 0.5 ? 3 : 1.5, 24);
            }
        });
    }

    const PRODUCTS = [
        { label: 'PVC PIPE', hex: '#3B82F6', pos: [-4.6,  1.6, -1.5] },
        { label: 'ELBOW', hex: '#8B5CF6', pos: [ 4.8,  2.1, -2.0] },
        { label: 'TEE', hex: '#22D3EE', pos: [-3.6, -0.4,  1.6] },
        { label: 'VALVE', hex: '#3B82F6', pos: [ 3.9, -0.6,  1.9] },
        { label: 'FLANGE', hex: '#22D3EE', pos: [-5.5,  0.4,  0.4] },
        { label: 'MIXER', hex: '#8B5CF6', pos: [ 5.7,  0.5,  0.2] },
    ];

    const boxGeo = new THREE.BoxGeometry(0.78, 0.78, 0.78);
    const hoverables = [];   // meshes the raycaster checks

    PRODUCTS.forEach((p) => {
        const mat = new THREE.MeshStandardMaterial({
            map: productTexture(p.label, p.hex),
            roughness: 0.4, metalness: 0.25,
            emissive: new THREE.Color(p.hex), emissiveIntensity: 0.08,
        });
        const box = new THREE.Mesh(boxGeo, mat);
        box.position.set(...p.pos);
        box.rotation.set(Math.random() * 0.4, Math.random() * Math.PI, 0);
        box.userData = { kind: 'product', baseEmissive: 0.08, baseScale: 1 };
        scene.add(box);
        hoverables.push(box);
        float(box, 0.3, 0.3 + Math.random() * 0.25, 0.15 + Math.random() * 0.1);

        // holographic price tag hovering above each box
        const priceTex = makeCanvasTexture(128, 64, (ctx, w, h) => {
            ctx.fillStyle = 'rgba(12,22,48,0.55)';
            ctx.fillRect(0, 0, w, h);
            ctx.strokeStyle = 'rgba(34,211,238,0.8)'; ctx.lineWidth = 2;
            ctx.strokeRect(2, 2, w - 4, h - 4);
            ctx.font = '600 26px system-ui, sans-serif';
            ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
            ctx.fillStyle = '#A9EBFF';
            ctx.shadowColor = '#22D3EE'; ctx.shadowBlur = 10;
            ctx.fillText('₹ ' + (20 + Math.floor(Math.random() * 180)), w / 2, h / 2);
        });
        const tag = new THREE.Sprite(new THREE.SpriteMaterial({
            map: priceTex, transparent: true, opacity: 0.85, depthWrite: false,
        }));
        tag.scale.set(0.62, 0.31, 1);
        tag.position.set(p.pos[0], p.pos[1] + 0.72, p.pos[2]);
        scene.add(tag);
        float(tag, 0.3, 0.3, 0);
    });

    /* extra wireframe product cubes (pure decoration, super cheap) */
    const wireCubeGeo = new THREE.BoxGeometry(0.5, 0.5, 0.5);
    const wireCubeMat = wireMat(COL.cyan, 0.35);
    const wireCubeMatB = wireMat(COL.purple, 0.3);
    [[-6.6, 2.6, -4], [6.4, 3.1, -5], [-2.2, 3.4, -6], [2.4, 3.8, -5.5], [0.4, 2.8, -7]]
        .forEach((pos, i) => {
            const c = new THREE.Mesh(wireCubeGeo, i % 2 ? wireCubeMat : wireCubeMatB);
            c.position.set(...pos);
            scene.add(c);
            float(c, 0.4, 0.25 + i * 0.05, 0.2);
        });

    /* ── Wireframe shopping cart (neon blue, wheels rotate) ──── */

    const cart = new THREE.Group();
    const cartMat = wireMat(COL.blue, 0.7);

    const basket = new THREE.Mesh(new THREE.BoxGeometry(1.15, 0.6, 0.75, 3, 2, 2), cartMat);
    basket.position.y = 0.55;
    cart.add(basket);

    const handle = new THREE.Mesh(new THREE.BoxGeometry(0.06, 0.5, 0.06), cartMat);
    handle.position.set(-0.72, 0.75, 0);
    handle.rotation.z = 0.5;
    cart.add(handle);
    const handleBar = new THREE.Mesh(new THREE.BoxGeometry(0.06, 0.06, 0.8), cartMat);
    handleBar.position.set(-0.85, 0.97, 0);
    cart.add(handleBar);

    const wheelGeo = new THREE.TorusGeometry(0.14, 0.045, 6, 14);
    const wheels = [];
    [[-0.42, 0.31], [0.42, 0.31], [-0.42, -0.31], [0.42, -0.31]].forEach(([x, z]) => {
        const wheel = new THREE.Mesh(wheelGeo, cartMat);
        wheel.position.set(x, 0.14, z);
        cart.add(wheel);
        wheels.push(wheel);
    });

    cart.position.set(-2.6, -1.45, 0.4);
    cart.rotation.y = 0.7;
    scene.add(cart);
    float(cart, 0.12, 0.3, 0);

    /* ── Barcode with sweeping scanner line ──────────────────── */

    const barcodeTex = makeCanvasTexture(256, 128, (ctx, w, h) => {
        ctx.fillStyle = '#060C1E';
        ctx.fillRect(0, 0, w, h);
        ctx.fillStyle = '#C9DEFF';
        let x = 22;
        while (x < w - 22) {
            const bw = [2, 3, 5, 2, 4][Math.floor(Math.random() * 5)];
            ctx.fillRect(x, 18, bw, h - 52);
            x += bw + 2 + Math.floor(Math.random() * 4);
        }
        ctx.font = '500 17px monospace';
        ctx.textAlign = 'center';
        ctx.fillStyle = 'rgba(160,190,240,0.8)';
        ctx.fillText('8 902341 700117', w / 2, h - 14);
    });
    const barcode = new THREE.Mesh(
        new THREE.PlaneGeometry(1.5, 0.75),
        new THREE.MeshBasicMaterial({ map: barcodeTex, transparent: true, opacity: 0.92 })
    );
    barcode.position.set(2.7, 1.3, 0.6);
    barcode.rotation.y = -0.4;
    scene.add(barcode);
    float(barcode, 0.18, 0.35, 0);

    // scanner line — a thin emissive bar swept by animations.js
    const scanLine = new THREE.Mesh(
        new THREE.PlaneGeometry(1.5, 0.045),
        new THREE.MeshBasicMaterial({ color: COL.cyan, transparent: true, opacity: 0 })
    );
    scanLine.position.copy(barcode.position);
    scanLine.position.z += 0.012;
    scanLine.rotation.copy(barcode.rotation);
    scene.add(scanLine);

    /* ── Glowing QR code (subtle pulse) ──────────────────────── */

    const qrTex = makeCanvasTexture(256, 256, (ctx, w) => {
        ctx.fillStyle = '#060C1E';
        ctx.fillRect(0, 0, w, w);
        const cell = w / 21;
        ctx.fillStyle = '#7DD3FC';
        // deterministic pseudo-QR pattern
        let seed = 7;
        const rand = () => (seed = (seed * 16807) % 2147483647) / 2147483647;
        for (let r = 0; r < 21; r++)
            for (let c = 0; c < 21; c++)
                if (rand() > 0.52) ctx.fillRect(c * cell + 1, r * cell + 1, cell - 2, cell - 2);
        // three finder squares
        ctx.fillStyle = '#060C1E';
        [[0, 0], [14, 0], [0, 14]].forEach(([cx, cy]) =>
            ctx.fillRect(cx * cell, cy * cell, cell * 7, cell * 7));
        ctx.fillStyle = '#A5E8FF';
        [[0, 0], [14, 0], [0, 14]].forEach(([cx, cy]) => {
            ctx.fillRect(cx * cell, cy * cell, cell * 7, cell * 7);
            ctx.fillStyle = '#060C1E';
            ctx.fillRect((cx + 1) * cell, (cy + 1) * cell, cell * 5, cell * 5);
            ctx.fillStyle = '#A5E8FF';
            ctx.fillRect((cx + 2) * cell, (cy + 2) * cell, cell * 3, cell * 3);
        });
    });
    const qr = new THREE.Mesh(
        new THREE.PlaneGeometry(0.9, 0.9),
        new THREE.MeshBasicMaterial({ map: qrTex, transparent: true, opacity: 0.9 })
    );
    qr.position.set(-2.9, 2.2, -0.8);
    qr.rotation.y = 0.35;
    qr.userData = { kind: 'qr' };
    scene.add(qr);
    float(qr, 0.22, 0.28, 0);

    /* ── Holographic receipt ─────────────────────────────────── */
    /* Numbers "softly animate": we redraw the tiny canvas only
       once every ~2.4 s (see animations.js), not per frame.     */

    const receiptCanvas = document.createElement('canvas');
    receiptCanvas.width = 256; receiptCanvas.height = 512;
    const receiptCtx = receiptCanvas.getContext('2d');
    const receiptTex = new THREE.CanvasTexture(receiptCanvas);

    function drawReceipt(total) {
        const ctx = receiptCtx, w = 256, h = 512;
        ctx.clearRect(0, 0, w, h);
        // translucent holo body
        ctx.fillStyle = 'rgba(10, 20, 44, 0.72)';
        ctx.fillRect(0, 0, w, h);
        ctx.strokeStyle = 'rgba(59,130,246,0.7)';
        ctx.lineWidth = 3;
        ctx.strokeRect(4, 4, w - 8, h - 8);

        ctx.textAlign = 'center';
        ctx.fillStyle = '#D9E8FF';
        ctx.font = '700 30px system-ui, sans-serif';
        ctx.shadowColor = '#3B82F6'; ctx.shadowBlur = 14;
        ctx.fillText('LINGARAJ SANITARY', w / 2, 52);
        ctx.shadowBlur = 0;
        ctx.font = '400 15px monospace';
        ctx.fillStyle = 'rgba(150,180,230,0.85)';
        ctx.fillText('— RETAIL RECEIPT —', w / 2, 82);

        // dashed separator helper
        const dash = (y) => {
            ctx.strokeStyle = 'rgba(120,150,210,0.4)';
            ctx.setLineDash([6, 6]); ctx.lineWidth = 1.5;
            ctx.beginPath(); ctx.moveTo(22, y); ctx.lineTo(w - 22, y); ctx.stroke();
            ctx.setLineDash([]);
        };
        dash(102);

        ctx.font = '400 16px monospace';
        ctx.textAlign = 'left';
        ctx.fillStyle = 'rgba(190,210,245,0.9)';
        const items = [['PVC PIPE', '62.00'], ['ELBOW', '480.00'], ['TEE', '45.00'], ['VALVE', '38.00']];
        items.forEach(([name, amt], i) => {
            ctx.fillText(name, 30, 136 + i * 30);
            ctx.textAlign = 'right';
            ctx.fillText('₹ ' + amt, w - 30, 136 + i * 30);
            ctx.textAlign = 'left';
        });
        dash(258);

        ctx.font = '600 17px monospace';
        ctx.fillText('GST 18%', 30, 292);
        ctx.textAlign = 'right';
        ctx.fillText('₹ ' + (total * 0.18 / 1.18).toFixed(2), w - 30, 292);

        ctx.textAlign = 'left';
        ctx.font = '700 26px system-ui, sans-serif';
        ctx.shadowColor = '#22D3EE'; ctx.shadowBlur = 12;
        ctx.fillStyle = '#B8F1FF';
        ctx.fillText('TOTAL', 30, 342);
        ctx.textAlign = 'right';
        ctx.fillText('₹ ' + total.toFixed(2), w - 30, 342);
        ctx.shadowBlur = 0;

        // PAID pill
        ctx.fillStyle = 'rgba(34,211,238,0.14)';
        ctx.strokeStyle = 'rgba(34,211,238,0.8)';
        ctx.lineWidth = 2;
        const px = w / 2 - 52, py = 366;
        ctx.beginPath();
        ctx.roundRect ? ctx.roundRect(px, py, 104, 34, 17) : ctx.rect(px, py, 104, 34);
        ctx.fill(); ctx.stroke();
        ctx.font = '700 18px system-ui, sans-serif';
        ctx.textAlign = 'center';
        ctx.fillStyle = '#9FF3FF';
        ctx.fillText('PAID', w / 2, py + 24);

        // mini QR footer
        const cell = 6, ox = w / 2 - 42, oy = 420;
        let seed = 13;
        const rand = () => (seed = (seed * 16807) % 2147483647) / 2147483647;
        ctx.fillStyle = 'rgba(200,225,255,0.85)';
        for (let r = 0; r < 12; r++)
            for (let c = 0; c < 14; c++)
                if (rand() > 0.5) ctx.fillRect(ox + c * cell, oy + r * cell, cell - 1, cell - 1);

        receiptTex.needsUpdate = true;
    }
    drawReceipt(845.00);

    const receipt = new THREE.Mesh(
        new THREE.PlaneGeometry(1.15, 2.3),
        new THREE.MeshBasicMaterial({
            map: receiptTex, transparent: true, opacity: 0.94, side: THREE.DoubleSide,
        })
    );
    receipt.position.set(2.2, 0.9, -1.4);
    receipt.rotation.y = -0.3;
    scene.add(receipt);
    float(receipt, 0.24, 0.26, 0.1);

    /* ── Inventory shelves (left + right of the store) ───────── */

    function makeShelf() {
        const g = new THREE.Group();
        const frameMat = wireMat(COL.blue, 0.4);
        for (let i = 0; i < 3; i++) {
            const plank = new THREE.Mesh(new THREE.BoxGeometry(1.7, 0.05, 0.5), frameMat);
            plank.position.y = i * 0.55;
            g.add(plank);
            // little stock cubes on each plank
            for (let j = 0; j < 3; j++) {
                if (Math.random() > 0.65) continue;
                const stock = new THREE.Mesh(
                    new THREE.BoxGeometry(0.22, 0.22, 0.22),
                    new THREE.MeshStandardMaterial({
                        color: 0x14244A, roughness: 0.5,
                        emissive: [COL.blue, COL.purple, COL.cyan][j % 3],
                        emissiveIntensity: 0.35,
                    })
                );
                stock.position.set(-0.55 + j * 0.55, i * 0.55 + 0.14, 0);
                g.add(stock);
            }
        }
        // uprights
        [-0.85, 0.85].forEach((x) => {
            const post = new THREE.Mesh(new THREE.BoxGeometry(0.05, 1.35, 0.05), frameMat);
            post.position.set(x, 0.55, 0);
            g.add(post);
        });
        return g;
    }

    const shelfL = makeShelf();
    shelfL.position.set(-5.2, -1.4, -2.6);
    shelfL.rotation.y = 0.5;
    scene.add(shelfL);
    float(shelfL, 0.08, 0.2, 0);

    const shelfR = makeShelf();
    shelfR.position.set(5.1, -1.35, -3.0);
    shelfR.rotation.y = -0.45;
    scene.add(shelfR);
    float(shelfR, 0.08, 0.24, 0);

    /* ── Floating glass panels (reflection only, no content) ─── */

    const glassMat = new THREE.MeshPhysicalMaterial({
        color: 0xBFD8FF,
        transparent: true, opacity: 0.06,
        roughness: 0.08, metalness: 0.9,
        side: THREE.DoubleSide,
    });
    const glassEdge = wireMat(0x86AFFF, 0.22);

    [[-4.2, 2.9, -3.6, 0.4], [4.5, 1.1, -4.4, -0.35], [0.2, 4.0, -4.8, 0.1]]
        .forEach(([x, y, z, ry]) => {
            const panel = new THREE.Group();
            const pane = new THREE.Mesh(new THREE.PlaneGeometry(1.9, 1.15), glassMat);
            const edge = new THREE.Mesh(new THREE.PlaneGeometry(1.9, 1.15), glassEdge);
            panel.add(pane, edge);
            panel.position.set(x, y, z);
            panel.rotation.y = ry;
            scene.add(panel);
            float(panel, 0.2, 0.2, 0.05);
        });

    /* ── Particles (drift + gentle mouse avoidance) ──────────── */

    const P_COUNT = 180;
    const pGeo = new THREE.BufferGeometry();
    const pPos = new Float32Array(P_COUNT * 3);
    const pHome = new Float32Array(P_COUNT * 3);   // resting position
    for (let i = 0; i < P_COUNT; i++) {
        pHome[i * 3]     = pPos[i * 3]     = (Math.random() - 0.5) * 22;
        pHome[i * 3 + 1] = pPos[i * 3 + 1] = Math.random() * 9 - 1.8;
        pHome[i * 3 + 2] = pPos[i * 3 + 2] = (Math.random() - 0.5) * 16 - 2;
    }
    pGeo.setAttribute('position', new THREE.BufferAttribute(pPos, 3));

    const particles = new THREE.Points(pGeo, new THREE.PointsMaterial({
        color: 0x9EC7FF, size: 0.055, transparent: true, opacity: 0.7,
        sizeAttenuation: true, depthWrite: false,
    }));
    scene.add(particles);

    /* ── Public handle for the other modules ─────────────────── */

    window.DEVBILL = {
        renderer, scene, camera,
        floaters, wheels, grid,
        barcode, scanLine, qr, receipt, drawReceipt,
        particles, pPos, pHome, P_COUNT,
        hoverables, door, store,
        COL,
    };

    /* keep canvas + camera matched to the window */
    window.addEventListener('resize', () => {
        camera.aspect = window.innerWidth / window.innerHeight;
        camera.updateProjectionMatrix();
        renderer.setSize(window.innerWidth, window.innerHeight);
    });
})();
