# syntax=docker/dockerfile:1

# ---- build stage: Node compiles the React app into static files ----
FROM node:25-alpine@sha256:bdf2cca6fe3dabd014ea60163eca3f0f7015fbd5c7ee1b0e9ccb4ced6eb02ef4 AS build

WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci --no-audit --no-fund

COPY . .
# Commit SHA from CI, shown in the sidebar so a deploy can be verified in the browser.
ARG GIT_SHA=local
ENV VITE_GIT_SHA=${GIT_SHA}
RUN npm run build

# ---- runtime stage: nginx serves dist/; Node and node_modules are left behind ----
# nginx-unprivileged runs as uid 101 and listens on 8080 instead of 80.
FROM nginxinc/nginx-unprivileged:1.30-alpine@sha256:782bb89768cc87b7f95c18b95baa1af250e5d451f26794f59363540161147c01 AS runtime

# Rendered by the image entrypoint at start-up (envsubst of ${BACKEND_URL}).
COPY nginx/default.conf.template /etc/nginx/templates/default.conf.template
COPY --from=build /app/dist /usr/share/nginx/html

ENV BACKEND_URL=http://backend:8000

USER 101
EXPOSE 8080

HEALTHCHECK --interval=15s --timeout=3s --retries=3 \
  CMD ["wget", "-q", "-O", "/dev/null", "http://127.0.0.1:8080/healthz"]
