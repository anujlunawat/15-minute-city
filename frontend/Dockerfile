# Stage 1: Build the React application
FROM node:20-alpine as build

WORKDIR /app
COPY package*.json ./
RUN npm install

ARG VITE_API_BASE=http://localhost:8000

COPY . .
RUN npm run build

# Stage 2: Serve with Nginx
FROM nginx:alpine
# Copy the built files from the previous stage
COPY --from=build /app/dist /usr/share/nginx/html

# Expose port 80
EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
