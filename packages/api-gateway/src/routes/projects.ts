import { Router } from 'express';

export const projectsRouter = Router();

// GET /api/projects — List projects
projectsRouter.get('/', async (_req, res) => {
  // TODO: Query PostgreSQL for projects
  res.json({ projects: [] });
});

// POST /api/projects — Create project
projectsRouter.post('/', async (req, res) => {
  const { name, description } = req.body;
  // TODO: Insert into PostgreSQL
  res.status(201).json({ id: 'placeholder', name, description });
});

// GET /api/projects/:id — Get project details
projectsRouter.get('/:id', async (req, res) => {
  const { id } = req.params;
  // TODO: Query PostgreSQL
  res.json({ id, name: 'placeholder', description: '' });
});
