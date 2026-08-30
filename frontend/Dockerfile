# syntax=docker/dockerfile:1

##############################
# Stage 1: builder — install dev deps and build the static bundle
##############################
FROM node:18-alpine AS builder

WORKDIR /app

# Accept build-time variables
ARG VITE_API_URL
ARG VITE_GOOGLE_CLIENT_ID

# Set them as environment variables for Vite
ENV VITE_API_URL=$VITE_API_URL
ENV VITE_GOOGLE_CLIENT_ID=$VITE_GOOGLE_CLIENT_ID

COPY package*.json ./

RUN npm install --no-audit --no-fund

COPY . .

# Normalize line endings to avoid issues with Windows CRLF
RUN sed -i 's/\r$//' package.json

RUN npm run build

# Verify dist folder exists
RUN ls -la /app/dist/

##############################
# Stage 2: runtime
# Only the built static bundle and the static server are needed.
# health-server.cjs uses only Node built-ins, so no node_modules are required.
##############################
FROM node:18-alpine AS runtime

WORKDIR /app
ENV NODE_ENV=production

COPY --from=builder /app/dist ./dist
COPY health-server.cjs ./health-server.cjs

EXPOSE 5173

CMD ["node", "health-server.cjs"]
