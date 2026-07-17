(function () {
    'use strict';

    const body = document.body;
    const veil = document.getElementById('fade-veil');
    const title = document.getElementById('hud-title');
    const subtitle = document.getElementById('hud-subtitle');
    const hint = document.getElementById('hud-hint');
    const glow = document.getElementById('cursor-glow');
    const dot = document.getElementById('cursor-dot');

    let targetUrl = body.getAttribute('data-target');
    try {
        const storedTarget = sessionStorage.getItem('devbill_last_employee_url');
        if (storedTarget) {
            targetUrl = storedTarget;
            body.setAttribute('data-target', targetUrl);
        }
    } catch (e) {}

    if (!window.gsap || !window.THREE || !window.DEVBILL) {
        if (veil) {
            veil.style.opacity = '0';
            veil.style.transition = 'opacity 0.4s ease';
        }
        return;
    }

    const { gsap } = window;
    const { renderer, scene, camera, floaters, hoverables, door, store, barcode, scanLine, qr, receipt, drawReceipt, particles, pPos, pHome, P_COUNT, wheels } = window.DEVBILL;

    const pointer = { x: 0, y: 0 };
    const target = { x: 0, y: 0 };

    function revealLanding() {
        window.__devbillEntered = false;
        if (veil) {
            veil.style.opacity = '1';
            veil.style.transition = 'opacity 0.45s ease';
            gsap.to(veil, { opacity: 0, duration: 1.1, ease: 'power2.out' });
        }
        if (title) {
            gsap.to(title, { autoAlpha: 1, y: 0, duration: 1.1, ease: 'power3.out', delay: 0.3 });
        }
        if (subtitle) {
            gsap.to(subtitle, { autoAlpha: 1, y: 0, duration: 1.0, ease: 'power3.out', delay: 0.7 });
        }
        if (hint) {
            gsap.to(hint, { autoAlpha: 1, y: 0, duration: 1.0, ease: 'power3.out', delay: 1.0 });
        }
    }

    function updatePointer(event) {
        pointer.x = (event.clientX / window.innerWidth) * 2 - 1;
        pointer.y = -(event.clientY / window.innerHeight) * 2 + 1;
    }

    window.addEventListener('pointermove', (event) => {
        updatePointer(event);
        target.x = event.clientX;
        target.y = event.clientY;
    });

    document.addEventListener('dblclick', (event) => {
        event.preventDefault();
        enterExperience();
    });

    window.addEventListener('keydown', (event) => {
        if (event.key === 'Enter' || event.key === ' ') {
            event.preventDefault();
            enterExperience();
        }
    });

    window.addEventListener('pageshow', revealLanding);
    document.addEventListener('DOMContentLoaded', revealLanding);
    revealLanding();

    function enterExperience() {
        if (window.__devbillEntered) return;
        window.__devbillEntered = true;

        gsap.to(veil, { opacity: 1, duration: 0.8, ease: 'power2.in' });
        gsap.to(camera.position, {
            x: 0,
            y: 1.45,
            z: 8.8,
            duration: 1.35,
            ease: 'power2.inOut',
            onComplete: () => {
                if (targetUrl) {
                    window.location.href = targetUrl;
                }
            },
        });
        gsap.to(camera.rotation, { x: -0.05, y: 0, z: 0, duration: 1.35, ease: 'power2.inOut' });
        gsap.to(door.position, { z: 0.95, duration: 0.9, ease: 'power2.inOut' });
        gsap.to(store.scale, { x: 0.95, y: 0.95, z: 0.95, duration: 0.8, ease: 'power2.inOut' });
    }

    gsap.set([title, subtitle, hint], { autoAlpha: 0, y: 18 });
    revealLanding();

    const clock = new THREE.Clock();
    const raycaster = new THREE.Raycaster();
    const mouse = new THREE.Vector2();

    function animate() {
        const elapsed = clock.getElapsedTime();

        floaters.forEach((item) => {
            item.obj.position.y = item.baseY + Math.sin(elapsed * item.speed + item.phase) * item.amp;
            item.obj.rotation.y += item.rot * 0.01;
        });

        if (wheels && wheels.length) {
            wheels.forEach((wheel) => {
                wheel.rotation.x += 0.02;
            });
        }

        if (barcode && scanLine) {
            const scan = 0.5 + Math.sin(elapsed * 2.2) * 0.5;
            scanLine.material.opacity = 0.9;
            scanLine.position.y = barcode.position.y + (scan - 0.5) * 0.07;
        }

        if (qr) {
            qr.material.opacity = 0.85 + Math.sin(elapsed * 1.5) * 0.08;
        }

        if (receipt && drawReceipt) {
            if (Math.floor(elapsed * 0.8) % 2 === 0) {
                drawReceipt(845.0 + Math.sin(elapsed * 0.5) * 6.0);
            }
        }

        const particlesCount = Math.min(P_COUNT, particles.geometry.attributes.position.count);
        for (let i = 0; i < particlesCount; i++) {
            const idx = i * 3;
            const homeX = pHome[idx];
            const homeY = pHome[idx + 1];
            const homeZ = pHome[idx + 2];
            const offset = Math.sin(elapsed * 0.5 + i) * 0.03;
            pPos[idx] = homeX + Math.sin(elapsed * 0.2 + i * 0.17) * 0.06 + pointer.x * 0.2 + offset;
            pPos[idx + 1] = homeY + Math.sin(elapsed * 0.25 + i * 0.19) * 0.04 + pointer.y * 0.08;
            pPos[idx + 2] = homeZ + Math.cos(elapsed * 0.18 + i * 0.11) * 0.05 + pointer.x * 0.04;
        }
        particles.geometry.attributes.position.needsUpdate = true;

        if (hoverables && hoverables.length) {
            mouse.x = pointer.x;
            mouse.y = pointer.y;
            raycaster.setFromCamera(mouse, camera);
            const intersects = raycaster.intersectObjects(hoverables, false);
            hoverables.forEach((mesh) => {
                const current = mesh.material.emissiveIntensity ?? 0;
                const targetVal = intersects.some((hit) => hit.object === mesh) ? 0.28 : mesh.userData.baseEmissive ?? 0.08;
                if (Math.abs(current - targetVal) > 0.001) {
                    gsap.to(mesh.material, { emissiveIntensity: targetVal, duration: 0.25, ease: 'power2.out' });
                }
            });
        }

        if (glow && dot) {
            glow.style.transform = `translate(${target.x}px, ${target.y}px)`;
            dot.style.transform = `translate(${target.x}px, ${target.y}px)`;
        }

        renderer.render(scene, camera);
        requestAnimationFrame(animate);
    }

    animate();
})();
