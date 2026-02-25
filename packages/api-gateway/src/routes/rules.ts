import { Router } from 'express';

export const rulesRouter = Router();

// GET /api/rules — List business rules for a project
rulesRouter.get('/', async (req, res) => {
  const { projectId, type } = req.query;
  // TODO: Query PostgreSQL, optionally filter by type
  res.json({ rules: [] });
});

// GET /api/rules/:id — Get rule with source code
rulesRouter.get('/:id', async (req, res) => {
  const { id } = req.params;
  // TODO: Query PostgreSQL
  res.json({ id, name: 'placeholder', sourceCode: '', type: 'finance_rule' });
});

// POST /api/rules — Create new rule
rulesRouter.post('/', async (req, res) => {
  const { projectId, name, type, sourceCode, targetRuntime } = req.body;
  // TODO: Insert into PostgreSQL artefacts table
  res.status(201).json({ id: 'placeholder', projectId, name, type, targetRuntime });
});

// PUT /api/rules/:id — Update rule source
rulesRouter.put('/:id', async (req, res) => {
  const { id } = req.params;
  const { sourceCode } = req.body;
  // TODO: Update PostgreSQL, increment version
  res.json({ id, updated: true });
});

// POST /api/rules/:id/compile — Compile and validate via Roslyn service
rulesRouter.post('/:id/compile', async (req, res) => {
  const { id } = req.params;
  // TODO: Send source to Roslyn service, return compilation result
  res.json({ success: true, errors: [], warnings: [], deprecatedApis: [] });
});
