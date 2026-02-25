FROM node:20-slim

WORKDIR /app

COPY packages/api-gateway/package.json .
RUN npm install --production

COPY packages/api-gateway/ .
RUN npm run build

EXPOSE 4000

CMD ["node", "dist/server.js"]
