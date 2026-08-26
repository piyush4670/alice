/* A tiny shared audio-level bucket.

The voice engine writes a live 0..1 level here every animation frame; the
visualizer and the orb read it. Kept out of the observable store so that a
60 Hz audio stream never churns the state machine that drives the UI.
*/

export const level = {
  value: 0,     // 0..1 live microphone / broadcast level
  source: "idle", // "idle" | "mic" | "speak"
};
