(function () {
    'use strict';

    if (!window.DEVBILL) {
        return;
    }

    const { door, store, barcode, scanLine, qr, receipt, drawReceipt } = window.DEVBILL;
    const clock = new THREE.Clock();

    function animate() {
        const elapsed = clock.getElapsedTime();

        if (store) {
            store.rotation.y = Math.sin(elapsed * 0.2) * 0.04;
        }

        if (door) {
            door.material.opacity = 0.85 + Math.sin(elapsed * 1.4) * 0.05;
        }

        if (barcode && scanLine) {
            const scan = 0.5 + Math.sin(elapsed * 2.0) * 0.5;
            scanLine.material.opacity = 0.8;
            scanLine.position.y = barcode.position.y + (scan - 0.5) * 0.06;
        }

        if (qr) {
            qr.material.opacity = 0.82 + Math.sin(elapsed * 1.3) * 0.08;
        }

        if (receipt && drawReceipt) {
            drawReceipt(845.0 + Math.sin(elapsed * 0.4) * 5.0);
        }

        requestAnimationFrame(animate);
    }

    animate();
})();
