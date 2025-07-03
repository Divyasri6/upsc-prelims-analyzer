# Stage 1: Build the React app
FROM node:18-alpine AS builder

WORKDIR /app

COPY package*.json ./
RUN npm install

COPY . ./
RUN npm run build

# Stage 2: Serve with a static file server
FROM nginx:stable-alpine

# Copy build artifacts from builder
COPY --from=builder /app/build /usr/share/nginx/html

# Optional: Customize NGINX config if needed
EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]