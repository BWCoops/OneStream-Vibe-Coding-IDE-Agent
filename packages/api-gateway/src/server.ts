import express from 'express';
import cors from 'cors';
import helmet from 'helmet';
import morgan from 'morgan';
import { createServer } from 'http';
import { Server as SocketIOServer } from 'socket.io';
import { config } from './config.js';
import { healthRouter } from './routes/health.js';
import { projectsRouter } from './routes/projects.js';
import { rulesRouter } from './routes/rules.js';
import { environmentsRouter } from './routes/environments.js';
import { pipelinesRouter } from './routes/pipelines.js';
import { auditRouter } from './routes/audit.js';
import { chatRouter } from './routes/chat.js';
import { errorHandler } from './middleware/error-handler.js';
import { setupWebSocket } from './websocket/handler.js';

const app = express();
const httpServer = createServer(app);
const io = new SocketIOServer(httpServer, {
  cors: { origin: config.corsOrigin, methods: ['GET', 'POST'] },
});

// Middleware
app.use(helmet());
app.use(cors({ origin: config.corsOrigin }));
app.use(morgan('combined'));
app.use(express.json({ limit: '10mb' }));

// Routes
app.use('/api/health', healthRouter);
app.use('/api/projects', projectsRouter);
app.use('/api/rules', rulesRouter);
app.use('/api/environments', environmentsRouter);
app.use('/api/pipelines', pipelinesRouter);
app.use('/api/audit', auditRouter);
app.use('/api/chat', chatRouter);

// Error handling (must be last)
app.use(errorHandler);

// WebSocket (Yjs sync + streaming)
setupWebSocket(io);

httpServer.listen(config.port, () => {
  console.log(`API Gateway running on port ${config.port}`);
});

export { app, httpServer };
