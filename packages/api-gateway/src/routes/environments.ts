import { Router } from 'express';
import { query } from '../db.js';

export const environmentsRouter = Router();

// GET /api/environments
environmentsRouter.get('/', async (_req, res, next) => {
  try {
    const result = await query(
      `SELECT id, name, type, url, api_version, platform_version,
              dotnet_runtime, sic_enabled, created_at, updated_at
       FROM environments
       ORDER BY type, name`,
    );
    res.json({ environments: result.rows });
  } catch (err) {
    next(err);
  }
});

// POST /api/environments — Register a new OneStream environment
environmentsRouter.post('/', async (req, res, next) => {
  try {
    const { name, type, url, apiVersion, patVaultPath, sicEnabled } = req.body;
    const result = await query(
      `INSERT INTO environments (name, type, url, api_version, pat_vault_path, sic_enabled)
       VALUES ($1, $2, $3, $4, $5, $6)
       RETURNING id, name, type, url, api_version, platform_version, dotnet_runtime, sic_enabled, created_at`,
      [name, type, url, apiVersion ?? '7.2.0', patVaultPath, sicEnabled ?? false],
    );
    res.status(201).json(result.rows[0]);
  } catch (err) {
    next(err);
  }
});

// PUT /api/environments/:id/detect — Detect platform version
environmentsRouter.put('/:id/detect', async (req, res, next) => {
  try {
    const { id } = req.params;
    const envResult = await query('SELECT url, api_version FROM environments WHERE id = $1', [id]);
    if (envResult.rows.length === 0) {
      res.status(404).json({ error: 'Environment not found' });
      return;
    }

    // In production, this would call the OneStream API to detect version.
    // For now, accept it from the request body as a manual override.
    const { platformVersion, dotnetRuntime } = req.body;
    const result = await query(
      `UPDATE environments
       SET platform_version = $1, dotnet_runtime = $2, updated_at = NOW()
       WHERE id = $3
       RETURNING id, name, type, platform_version, dotnet_runtime`,
      [platformVersion, dotnetRuntime, id],
    );
    res.json(result.rows[0]);
  } catch (err) {
    next(err);
  }
});

// DELETE /api/environments/:id
environmentsRouter.delete('/:id', async (req, res, next) => {
  try {
    const { id } = req.params;
    await query('DELETE FROM environments WHERE id = $1', [id]);
    res.status(204).end();
  } catch (err) {
    next(err);
  }
});
