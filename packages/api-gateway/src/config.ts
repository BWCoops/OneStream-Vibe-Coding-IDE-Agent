import 'dotenv/config';

export const config = {
  port: parseInt(process.env.PORT ?? '4000', 10),
  corsOrigin: process.env.CORS_ORIGIN ?? 'http://localhost:3000',
  jwtSecret: process.env.JWT_SECRET ?? 'change-me-in-production',
  databaseUrl: process.env.DATABASE_URL ?? 'postgresql://ide_agent:localdev@localhost:5432/onestream_ide',
  redisUrl: process.env.REDIS_URL ?? 'redis://localhost:6379',
  orchestratorUrl: process.env.ORCHESTRATOR_URL ?? 'http://localhost:8080',
} as const;
