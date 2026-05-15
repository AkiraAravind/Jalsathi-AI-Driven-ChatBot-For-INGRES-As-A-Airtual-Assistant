# Build stage
FROM node:20-alpine as build
WORKDIR /app

# Copy root configurations (if any) and frontend package
COPY package*.json ./
RUN npm install

COPY . .

# Build Vite app
RUN npm run build

# Serve stage
FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
