import { Router } from 'express';
import { query, transaction } from '../db.js';

export const pipelinesRouter = Router();

// GET /api/pipelines
pipelinesRouter.get('/', async (req, res, next) => {
  try {
    const { projectId } = req.query;
    let sql = `SELECT id, project_id, name, description, schedule,
                      sla_target_minutes, status, created_at, updated_at
               FROM pipelines`;
    const params: unknown[] = [];

    if (projectId) {
      sql += ' WHERE project_id = $1';
      params.push(projectId);
    }
    sql += ' ORDER BY updated_at DESC';

    const result = await query(sql, params);
    res.json({ pipelines: result.rows });
  } catch (err) {
    next(err);
  }
});

// GET /api/pipelines/:id — Get pipeline with full definition
pipelinesRouter.get('/:id', async (req, res, next) => {
  try {
    const { id } = req.params;
    const result = await query(
      `SELECT id, project_id, name, description, definition, schedule,
              sla_target_minutes, status, created_at, updated_at
       FROM pipelines WHERE id = $1`,
      [id],
    );
    if (result.rows.length === 0) {
      res.status(404).json({ error: 'Pipeline not found' });
      return;
    }
    res.json(result.rows[0]);
  } catch (err) {
    next(err);
  }
});

// POST /api/pipelines — Create pipeline
pipelinesRouter.post('/', async (req, res, next) => {
  try {
    const { projectId, name, description, definition, schedule, slaTargetMinutes } = req.body;
    const result = await query(
      `INSERT INTO pipelines (project_id, name, description, definition, schedule, sla_target_minutes)
       VALUES ($1, $2, $3, $4, $5, $6)
       RETURNING id, project_id, name, status, created_at`,
      [projectId, name, description, JSON.stringify(definition), JSON.stringify(schedule), slaTargetMinutes],
    );
    res.status(201).json(result.rows[0]);
  } catch (err) {
    next(err);
  }
});

// POST /api/pipelines/:id/execute — Trigger pipeline execution
pipelinesRouter.post('/:id/execute', async (req, res, next) => {
  try {
    const { id } = req.params;
    const pipelineResult = await query('SELECT id, definition FROM pipelines WHERE id = $1', [id]);
    if (pipelineResult.rows.length === 0) {
      res.status(404).json({ error: 'Pipeline not found' });
      return;
    }

    const execution = await query(
      `INSERT INTO pipeline_executions (pipeline_id, status)
       VALUES ($1, 'running')
       RETURNING id, pipeline_id, status, started_at`,
      [id],
    );
    res.status(202).json(execution.rows[0]);
  } catch (err) {
    next(err);
  }
});

// GET /api/pipelines/:id/executions — List pipeline executions
pipelinesRouter.get('/:id/executions', async (req, res, next) => {
  try {
    const { id } = req.params;
    const result = await query(
      `SELECT id, pipeline_id, status, started_at, completed_at, sla_met, error_details
       FROM pipeline_executions
       WHERE pipeline_id = $1
       ORDER BY started_at DESC
       LIMIT 50`,
      [id],
    );
    res.json({ executions: result.rows });
  } catch (err) {
    next(err);
  }
});
