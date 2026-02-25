import { Router } from 'express';
import { query } from '../db.js';

export const auditRouter = Router();

// GET /api/audit — Query audit log (append-only, no mutations)
auditRouter.get('/', async (req, res, next) => {
  try {
    const { entityType, entityId, actor, limit: limitStr } = req.query;
    let sql = `SELECT id, event_type, entity_type, entity_id, actor, action,
                      details, previous_hash, entry_hash, created_at
               FROM audit_log WHERE 1=1`;
    const params: unknown[] = [];
    let idx = 1;

    if (entityType) {
      sql += ` AND entity_type = $${idx++}`;
      params.push(entityType);
    }
    if (entityId) {
      sql += ` AND entity_id = $${idx++}`;
      params.push(entityId);
    }
    if (actor) {
      sql += ` AND actor = $${idx++}`;
      params.push(actor);
    }

    sql += ' ORDER BY created_at DESC';
    const limit = Math.min(parseInt(String(limitStr ?? '100'), 10), 1000);
    sql += ` LIMIT $${idx++}`;
    params.push(limit);

    const result = await query(sql, params);
    res.json({ entries: result.rows, count: result.rows.length });
  } catch (err) {
    next(err);
  }
});

// GET /api/audit/verify — Verify audit chain integrity
auditRouter.get('/verify', async (_req, res, next) => {
  try {
    const result = await query(
      `SELECT id, entry_hash, previous_hash
       FROM audit_log
       ORDER BY id ASC`,
    );

    let valid = true;
    let brokenAt: number | null = null;
    const rows = result.rows;

    for (let i = 1; i < rows.length; i++) {
      if (rows[i].previous_hash && rows[i].previous_hash !== rows[i - 1].entry_hash) {
        valid = false;
        brokenAt = rows[i].id;
        break;
      }
    }

    res.json({
      valid,
      totalEntries: rows.length,
      brokenAt,
    });
  } catch (err) {
    next(err);
  }
});
