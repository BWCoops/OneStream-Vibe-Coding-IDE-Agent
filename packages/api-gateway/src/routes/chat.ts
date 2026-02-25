import { Router } from 'express';
import { config } from '../config.js';

export const chatRouter = Router();

// POST /api/chat — Send message to orchestrator
chatRouter.post('/', async (req, res) => {
  const { message, projectId, environmentId } = req.body;

  try {
    // Forward to Python orchestrator service
    const response = await fetch(`${config.orchestratorUrl}/api/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message, projectId, environmentId }),
    });

    if (!response.ok) {
      throw new Error(`Orchestrator returned ${response.status}`);
    }

    const data = await response.json();
    res.json(data);
  } catch (error) {
    res.status(502).json({
      error: 'Orchestrator unavailable',
      message: error instanceof Error ? error.message : 'Unknown error',
    });
  }
});
