import { Router } from 'express';
import { query, transaction } from '../db.js';

export const rulesRouter = Router();

// GET /api/rules — List business rules for a project
rulesRouter.get('/', async (req, res, next) => {
  try {
    const { projectId, type, status } = req.query;
    let sql = `SELECT id, project_id, type, name, target_runtime, version,
                      status, git_sha, created_by, created_at, updated_at
               FROM artefacts WHERE 1=1`;
    const params: unknown[] = [];
    let idx = 1;

    if (projectId) {
      sql += ` AND project_id = $${idx++}`;
      params.push(projectId);
    }
    if (type) {
      sql += ` AND type = $${idx++}`;
      params.push(type);
    }
    if (status) {
      sql += ` AND status = $${idx++}`;
      params.push(status);
    }

    sql += ' ORDER BY updated_at DESC';
    const result = await query(sql, params);
    res.json({ rules: result.rows });
  } catch (err) {
    next(err);
  }
});

// GET /api/rules/:id — Get rule with source code
rulesRouter.get('/:id', async (req, res, next) => {
  try {
    const { id } = req.params;
    const result = await query(
      `SELECT id, project_id, type, name, source_code, target_runtime,
              version, status, git_sha, created_by, created_at, updated_at
       FROM artefacts WHERE id = $1`,
      [id],
    );
    if (result.rows.length === 0) {
      res.status(404).json({ error: 'Rule not found' });
      return;
    }
    res.json(result.rows[0]);
  } catch (err) {
    next(err);
  }
});

// POST /api/rules — Create new rule
rulesRouter.post('/', async (req, res, next) => {
  try {
    const { projectId, name, type, sourceCode, targetRuntime, createdBy } = req.body;
    const result = await transaction(async (client) => {
      const insert = await client.query(
        `INSERT INTO artefacts (project_id, type, name, source_code, target_runtime, created_by)
         VALUES ($1, $2, $3, $4, $5, $6)
         RETURNING id, project_id, type, name, target_runtime, version, status, created_at`,
        [projectId, type, name, sourceCode ?? '', targetRuntime ?? 'net8.0', createdBy ?? 'system'],
      );

      const artefact = insert.rows[0];

      // Immutable audit log entry
      await client.query(
        `INSERT INTO audit_log (event_type, entity_type, entity_id, actor, action, details, entry_hash)
         VALUES ('artefact', 'business_rule', $1, $2, 'create', $3,
                 encode(sha256(($4 || $1 || 'create')::bytea), 'hex'))`,
        [artefact.id, createdBy ?? 'system', JSON.stringify({ name, type }), Date.now().toString()],
      );

      return artefact;
    });
    res.status(201).json(result);
  } catch (err) {
    next(err);
  }
});

// PUT /api/rules/:id — Update rule source
rulesRouter.put('/:id', async (req, res, next) => {
  try {
    const { id } = req.params;
    const { sourceCode, updatedBy } = req.body;
    const result = await transaction(async (client) => {
      const update = await client.query(
        `UPDATE artefacts
         SET source_code = $1, version = version + 1, updated_at = NOW(), status = 'draft'
         WHERE id = $2
         RETURNING id, name, version, status, updated_at`,
        [sourceCode, id],
      );

      if (update.rows.length === 0) {
        throw new Error('Rule not found');
      }

      await client.query(
        `INSERT INTO audit_log (event_type, entity_type, entity_id, actor, action, details, entry_hash)
         VALUES ('artefact', 'business_rule', $1, $2, 'update', $3,
                 encode(sha256(($4 || $1 || 'update')::bytea), 'hex'))`,
        [id, updatedBy ?? 'system', JSON.stringify({ version: update.rows[0].version }), Date.now().toString()],
      );

      return update.rows[0];
    });
    res.json(result);
  } catch (err) {
    if (err instanceof Error && err.message === 'Rule not found') {
      res.status(404).json({ error: 'Rule not found' });
      return;
    }
    next(err);
  }
});

// POST /api/rules/:id/compile — Compile via Roslyn service
rulesRouter.post('/:id/compile', async (req, res, next) => {
  try {
    const { id } = req.params;
    const ruleResult = await query(
      'SELECT source_code, target_runtime FROM artefacts WHERE id = $1',
      [id],
    );
    if (ruleResult.rows.length === 0) {
      res.status(404).json({ error: 'Rule not found' });
      return;
    }

    const rule = ruleResult.rows[0];
    const roslynUrl = process.env.ROSLYN_SERVICE_URL ?? 'http://localhost:5100';

    const [compileResponse, deprecatedResponse] = await Promise.all([
      fetch(`${roslynUrl}/api/compile`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          SourceCode: rule.source_code,
          Language: 'vb.net',
          TargetRuntime: rule.target_runtime,
        }),
      }),
      fetch(`${roslynUrl}/api/check-deprecated`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          SourceCode: rule.source_code,
          PlatformVersion: rule.target_runtime === 'net8.0' ? '9.0.0' : '7.5.0',
        }),
      }),
    ]);

    const compilation = await compileResponse.json();
    const deprecated = await deprecatedResponse.json();

    res.json({ ...compilation, deprecatedApis: deprecated });
  } catch (err) {
    next(err);
  }
});

// DELETE /api/rules/:id
rulesRouter.delete('/:id', async (req, res, next) => {
  try {
    const { id } = req.params;
    await query('DELETE FROM artefacts WHERE id = $1', [id]);
    res.status(204).end();
  } catch (err) {
    next(err);
  }
});
