# Build stage
FROM node:22-alpine AS builder

WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm ci

# Copy source code
COPY . .

# Build the application
RUN npm run build

# Production stage - serve with nginx
FROM nginx:alpine AS production

# Install envsubst for environment variable substitution
RUN apk add --no-cache gettext

# Copy nginx config template
COPY nginx.conf.template /etc/nginx/templates/default.conf.template

# Copy built assets from builder stage
COPY --from=builder /app/dist /usr/share/nginx/html

# Default backend URL (can be overridden with -e BACKEND_URL=...)
ENV BACKEND_URL=http://localhost:8000

# Expose port 3000
EXPOSE 3000

# Use envsubst to replace environment variables in nginx config, then start nginx
CMD ["/bin/sh", "-c", "envsubst '${BACKEND_URL}' < /etc/nginx/templates/default.conf.template > /etc/nginx/conf.d/default.conf && nginx -g 'daemon off;'"]
