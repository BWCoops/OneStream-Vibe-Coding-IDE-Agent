import type { Server as SocketIOServer } from 'socket.io';

export function setupWebSocket(io: SocketIOServer): void {
  // Yjs document sync namespace
  const yjsNamespace = io.of('/yjs');
  yjsNamespace.on('connection', (socket) => {
    console.log(`Yjs client connected: ${socket.id}`);

    socket.on('join-document', (documentId: string) => {
      socket.join(documentId);
      console.log(`Client ${socket.id} joined document ${documentId}`);
    });

    socket.on('yjs-update', (documentId: string, update: Uint8Array) => {
      socket.to(documentId).emit('yjs-update', documentId, update);
    });

    socket.on('disconnect', () => {
      console.log(`Yjs client disconnected: ${socket.id}`);
    });
  });

  // AI chat streaming namespace
  const chatNamespace = io.of('/chat');
  chatNamespace.on('connection', (socket) => {
    console.log(`Chat client connected: ${socket.id}`);

    socket.on('message', async (data: { message: string; projectId: string }) => {
      // TODO: Stream response from orchestrator via SSE/WebSocket
      socket.emit('response-start', { messageId: crypto.randomUUID() });
      socket.emit('response-chunk', { content: 'Orchestrator not yet connected.' });
      socket.emit('response-end');
    });

    socket.on('disconnect', () => {
      console.log(`Chat client disconnected: ${socket.id}`);
    });
  });
}
