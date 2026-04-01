/**
 * WebSocket text message passed to IPC subscribers.
 * Matches the subset of MessageEvent consumed from the events socket.
 */
export interface IPCEvent {
  data: string
}
