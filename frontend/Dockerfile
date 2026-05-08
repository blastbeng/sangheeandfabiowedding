FROM node:18-alpine

WORKDIR /app

# Accept build-time variables
ARG VITE_API_URL
ARG VITE_GOOGLE_CLIENT_ID

# Set them as environment variables for Vite
ENV VITE_API_URL=$VITE_API_URL
ENV VITE_GOOGLE_CLIENT_ID=$VITE_GOOGLE_CLIENT_ID

COPY package*.json ./

RUN rm -rf node_modules package-lock.json
RUN npm install

COPY . .

# Normalize line endings to avoid issues with Windows CRLF
RUN sed -i 's/\r$//' package.json

RUN npm run build

# Verify dist folder exists
RUN ls -la /app/dist/

EXPOSE 5173

CMD ["npm", "run", "serve"]
