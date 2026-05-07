FROM node:18-alpine

WORKDIR /app

COPY package*.json ./

RUN npm install

COPY . .

RUN npm run build

# Verify dist folder exists
RUN ls -la /app/dist/

EXPOSE 5173

CMD ["npm", "run", "serve"]
