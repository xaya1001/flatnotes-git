import { ref, onMounted, onUnmounted } from 'vue';

export function usePanAndZoom(svgElementRef, containerElementRef) {
  const scale = ref(1);
  const panX = ref(0);
  const panY = ref(0);
  let isPanning = false;
  let startX = 0;
  let startY = 0;

  const updateTransform = () => {
    if (svgElementRef.value) {
      svgElementRef.value.style.transform = `scale(${scale.value}) translate(${panX.value}px, ${panY.value}px)`;
    }
  };

  const zoomIn = (factor = 1.2) => {
    scale.value *= factor;
    updateTransform();
  };

  const zoomOut = (factor = 1.2) => {
    scale.value /= factor;
    updateTransform();
  };

  const reset = () => {
    scale.value = 1;
    panX.value = 0;
    panY.value = 0;
    updateTransform();
  };

  const onMouseDown = (event) => {
    if (event.button !== 0) return; // Only handle left mouse button
    isPanning = true;
    startX = event.clientX - panX.value * scale.value; // Adjust startX by current pan and scale
    startY = event.clientY - panY.value * scale.value; // Adjust startY by current pan and scale
    if (containerElementRef.value) {
      containerElementRef.value.style.cursor = 'grabbing';
    }
  };

  const onMouseMove = (event) => {
    if (!isPanning || !containerElementRef.value) return;
    // Calculate new pan values based on mouse movement, adjusted for scale
    panX.value = (event.clientX - startX) / scale.value;
    panY.value = (event.clientY - startY) / scale.value;
    updateTransform();
  };

  const onMouseUp = () => {
    if (!isPanning) return;
    isPanning = false;
    if (containerElementRef.value) {
      containerElementRef.value.style.cursor = 'grab';
    }
  };

  const onWheel = (event) => {
    if (!containerElementRef.value || !containerElementRef.value.contains(event.target)) {
      return;
    }
    event.preventDefault();
    const delta = event.deltaY > 0 ? -1 : 1; // -1 for zoom out, 1 for zoom in
    const zoomFactor = 1.1;
    if (delta > 0) {
      scale.value *= zoomFactor;
    } else {
      scale.value /= zoomFactor;
    }
    updateTransform();
  };

  onMounted(() => {
    if (containerElementRef.value) {
      containerElementRef.value.style.cursor = 'grab';
      containerElementRef.value.addEventListener('mousedown', onMouseDown);
      document.addEventListener('mousemove', onMouseMove); // Listen on document for smoother panning
      document.addEventListener('mouseup', onMouseUp);     // Listen on document
      containerElementRef.value.addEventListener('wheel', onWheel, { passive: false });
    }
    updateTransform(); // Initial transform setup
  });

  onUnmounted(() => {
    if (containerElementRef.value) {
      containerElementRef.value.removeEventListener('mousedown', onMouseDown);
      document.removeEventListener('mousemove', onMouseMove);
      document.removeEventListener('mouseup', onMouseUp);
      containerElementRef.value.removeEventListener('wheel', onWheel);
    }
  });

  return {
    scale,
    panX,
    panY,
    zoomIn,
    zoomOut,
    reset,
    isPanning, // expose for potential external use or debugging
  };
}
