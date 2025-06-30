// client/components/toastui/composables/usePanAndZoom.spec.js
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { usePanAndZoom } from './usePanAndZoom.js';
import { ref } from 'vue';

describe('usePanAndZoom', () => {
  let svgElement;
  let containerElement;
  let svgElementRef;
  let containerElementRef;

  beforeEach(() => {
    // Create mock DOM elements
    svgElement = document.createElementNS("http://www.w3.org/2000/svg", "svg");
    containerElement = document.createElement('div');
    document.body.appendChild(containerElement);
    containerElement.appendChild(svgElement); // SVG needs to be in the container for some tests

    // Create Vue refs for the elements
    svgElementRef = ref(svgElement);
    containerElementRef = ref(containerElement);

    // Mock requestAnimationFrame for immediate execution if needed by underlying libraries
    // vi.spyOn(window, 'requestAnimationFrame').mockImplementation(cb => cb());
  });

  afterEach(() => {
    // Clean up DOM elements
    if (containerElement.parentNode) {
      containerElement.parentNode.removeChild(containerElement);
    }
    // window.requestAnimationFrame.mockRestore();
    vi.clearAllMocks();
  });

  it('should initialize with default scale and pan values', () => {
    const { scale, panX, panY } = usePanAndZoom(svgElementRef, containerElementRef);
    expect(scale.value).toBe(1);
    expect(panX.value).toBe(0);
    expect(panY.value).toBe(0);
    expect(svgElement.style.transform).toBe('scale(1) translate(0px, 0px)');
  });

  it('zoomIn should increase scale and update transform', () => {
    const { zoomIn, scale } = usePanAndZoom(svgElementRef, containerElementRef);
    zoomIn(1.5);
    expect(scale.value).toBe(1.5);
    expect(svgElement.style.transform).toBe('scale(1.5) translate(0px, 0px)');
  });

  it('zoomOut should decrease scale and update transform', () => {
    const { zoomOut, scale } = usePanAndZoom(svgElementRef, containerElementRef);
    zoomOut(1.5);
    expect(scale.value).toBe(1 / 1.5);
    expect(svgElement.style.transform).toMatch(/scale\(0\.666.*\)/); // Check for approximate scale
  });

  it('reset should restore default scale and pan values and update transform', () => {
    const { zoomIn, reset, scale, panX, panY } = usePanAndZoom(svgElementRef, containerElementRef);
    zoomIn(2); // Zoom in first
    panX.value = 10; // Apply some panning
    panY.value = 10;
    reset();
    expect(scale.value).toBe(1);
    expect(panX.value).toBe(0);
    expect(panY.value).toBe(0);
    expect(svgElement.style.transform).toBe('scale(1) translate(0px, 0px)');
  });

  // Basic Panning Tests (more detailed tests would require simulating mouse events)
  it('onMouseDown should set isPanning to true and cursor to grabbing', () => {
    const { isPanning } = usePanAndZoom(svgElementRef, containerElementRef);
    const event = new MouseEvent('mousedown', { button: 0 });
    containerElement.dispatchEvent(event); // Dispatch event on the container
    expect(isPanning.value).toBe(true);
    expect(containerElement.style.cursor).toBe('grabbing');
  });


  it('onMouseUp should set isPanning to false and cursor to grab', () => {
    const { isPanning } = usePanAndZoom(svgElementRef, containerElementRef);
    // Simulate mousedown first
    containerElement.dispatchEvent(new MouseEvent('mousedown', { button: 0 }));
    expect(isPanning.value).toBe(true); // Pre-condition

    // Dispatch mouseup on the document as per implementation
    document.dispatchEvent(new MouseEvent('mouseup'));
    expect(isPanning.value).toBe(false);
    expect(containerElement.style.cursor).toBe('grab');
  });

  it('onWheel should adjust scale (zoom in)', () => {
    const { scale } = usePanAndZoom(svgElementRef, containerElementRef);
    const initialScale = scale.value;
    const event = new WheelEvent('wheel', { deltaY: -100, bubbles: true }); // Negative deltaY for zoom in
    containerElement.dispatchEvent(event);
    expect(scale.value).toBeGreaterThan(initialScale);
  });

  it('onWheel should adjust scale (zoom out)', () => {
    const { scale } = usePanAndZoom(svgElementRef, containerElementRef);
    const initialScale = scale.value;
    const event = new WheelEvent('wheel', { deltaY: 100, bubbles: true }); // Positive deltaY for zoom out
    containerElement.dispatchEvent(event);
    expect(scale.value).toBeLessThan(initialScale);
  });

  // Note: Testing onMouseMove requires more complex event simulation (clientX/Y changes)
  // and ensuring the listeners are correctly attached, which can be tricky if onMounted/onUnmounted
  // are not behaving as expected in the test environment without a full Vue app mount.
  // The current tests cover the core logic of zoom/pan state changes.
});
