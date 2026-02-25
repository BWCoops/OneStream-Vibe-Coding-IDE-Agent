import { Router } from 'express';
import { query } from '../db.js';

export const projectsRouter = Router();

// GET /api/projects — List projects
projectsRouter.get('/', async (_req, res, next) => {
  try {
    const result = await query(
      `SELECT p.id, p.name, p.description, p.default_environment_id,
              p.created_at, p.updated_at
       FROM projects p
       ORDER BY p.updated_at DESC`,
    );
    res.json({ projects: result.rows });
  } catch (err) {
    next(err);
  }
});

// POST /api/projects — Create project
projectsRouter.post('/', async (req, res, next) => {
  try {
    const { name, description, defaultEnvironmentId } = req.body;
    const result = await query(
      `INSERT INTO projects (name, description, default_environment_id)
       VALUES ($1, $2, $3)
       RETURNING id, name, description, default_environment_id, created_at`,
      [name, description, defaultEnvironmentId ?? null],
    );
    res.status(201).json(result.rows[0]);
  } catch (err) {
    next(err);
  }
});

// GET /api/projects/:id — Get project with environments
projectsRouter.get('/:id', async (req, res, next) => {
  try {
    const { id } = req.params;
    const projectResult = await query(
      `SELECT id, name, description, default_environment_id, created_at, updated_at
       FROM projects WHERE id = $1`,
      [id],
    );
    if (projectResult.rows.length === 0) {
      res.status(404).json({ error: 'Project not found' });
      return;
    }

    const envResult = await query(
      `SELECT id, name, type, url, api_version, platform_version,
              dotnet_runtime, sic_enabled, created_at
       FROM environments
       ORDER BY type`,
    );

    res.json({
      ...projectResult.rows[0],
      environments: envResult.rows,
    });
  } catch (err) {
    next(err);
  }
});

// PUT /api/projects/:id — Update project
projectsRouter.put('/:id', async (req, res, next) => {
  try {
    const { id } = req.params;
    const { name, description } = req.body;
    const result = await query(
      `UPDATE projects SET name = COALESCE($1, name), description = COALESCE($2, description),
              updated_at = NOW()
       WHERE id = $3
       RETURNING id, name, description, updated_at`,
      [name, description, id],
    );
    if (result.rows.length === 0) {
      res.status(404).json({ error: 'Project not found' });
      return;
    }
    res.json(result.rows[0]);
  } catch (err) {
    next(err);
  }
});

// DELETE /api/projects/:id
projectsRouter.delete('/:id', async (req, res, next) => {
  try {
    const { id } = req.params;
    await query('DELETE FROM projects WHERE id = $1', [id]);
    res.status(204).end();
  } catch (err) {
    next(err);
  }
});
