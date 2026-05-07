FROM node:18-alpine

WORKDIR /app

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
