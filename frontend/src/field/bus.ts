type WaveDetail = { x?: number; y?: number; reason: string };

class FieldBus extends EventTarget {
  pulse(detail: WaveDetail) {
    this.dispatchEvent(new CustomEvent<WaveDetail>("wave", { detail }));
  }
}

export const fieldBus = new FieldBus();

export function pulseField(reason: string, point?: { x: number; y: number }) {
  fieldBus.pulse({ reason, x: point?.x, y: point?.y });
}
