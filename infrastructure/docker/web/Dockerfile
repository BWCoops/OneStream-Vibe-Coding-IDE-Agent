FROM node:20-slim AS build

WORKDIR /app

COPY packages/web/package.json .
RUN npm install

COPY packages/web/ .
RUN npm run build

FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY infrastructure/docker/web/nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 3000

CMD ["nginx", "-g", "daemon off;"]
