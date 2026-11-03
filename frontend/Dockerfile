# syntax=docker/dockerfile:1

# ---- stage 1: build the static React bundle with Node ----
FROM node:24-alpine AS build
WORKDIR /app
COPY package.json package-lock.json ./
RUN --mount=type=cache,target=/root/.npm npm ci --no-audit --no-fund
COPY . .
RUN npm run build

# ---- stage 2: serve it with unprivileged nginx (uid 101, port 8080) — no Node in the runtime image ----
FROM nginxinc/nginx-unprivileged:1.31-alpine
# Pull Alpine security fixes released after the base image was built, and drop curl (unused: the
# healthcheck uses busybox wget). Trivy blocked the image on new brotli/curl CVEs before this.
USER root
RUN apk upgrade --no-cache && apk del --no-cache curl
# where /api is proxied to: the compose service name, or the Kubernetes backend Service
ENV BACKEND_URL=http://backend:8000
COPY nginx/default.conf.template /etc/nginx/templates/default.conf.template
COPY --from=build /app/dist /usr/share/nginx/html
USER 101
EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=3s CMD wget -q -O /dev/null http://127.0.0.1:8080/healthz || exit 1
