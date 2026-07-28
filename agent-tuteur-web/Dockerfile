# Image web : build statique du SPA Vue (Node) puis service par nginx.
# L'image sert les fichiers statiques ET proxifie /api + /health vers l'API,
# ce qui la rend self-contained : utilisable telle quelle en dev (exposée sur
# un port) comme en prod (derrière le nginx frontal, qui route "/" vers elle).

FROM node:20-alpine AS build
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM nginx:1.27-alpine
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
