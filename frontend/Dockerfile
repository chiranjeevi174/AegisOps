# syntax=docker/dockerfile:1

# Stage 1: Build React Single Page Application
FROM node:22-alpine AS builder

WORKDIR /app

# Install dependencies using clean install from lockfile
COPY package.json package-lock.json ./
RUN npm ci

# Copy frontend source code and configuration
COPY . ./

# Build production bundle with TypeScript check and Vite minification
RUN npm run build

# Stage 2: Minimal hardened Nginx runtime
FROM nginx:1.27-alpine AS runtime

# Remove default static pages
RUN rm -rf /usr/share/nginx/html/*

# Copy compiled SPA production assets from builder
COPY --from=builder /app/dist /usr/share/nginx/html

# Copy production reverse-proxy and security configuration
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Configure runtime permissions for non-root nginx execution
RUN touch /var/run/nginx.pid && \
    chown -R nginx:nginx /var/run/nginx.pid /var/cache/nginx /usr/share/nginx/html /etc/nginx/conf.d

USER nginx

EXPOSE 80

# Health check against dedicated internal endpoint
HEALTHCHECK --interval=15s --timeout=5s --start-period=5s --retries=3 \
    CMD wget -q -O /dev/null http://localhost:80/healthz || exit 1

CMD ["nginx", "-g", "daemon off;"]
