# ── build ────────────────────────────────────────────────────────────────────
FROM node:22-alpine AS build
WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci

COPY . .

# The Maps key is a browser key: it ships in the bundle by design and is
# protected by an HTTP-referrer restriction on the key itself, not by secrecy.
ARG NEXT_PUBLIC_MAPS_API_KEY=""
ENV NEXT_PUBLIC_MAPS_API_KEY=$NEXT_PUBLIC_MAPS_API_KEY

RUN npm run build

# ── serve ────────────────────────────────────────────────────────────────────
FROM nginx:1.27-alpine
RUN rm -rf /usr/share/nginx/html/* /etc/nginx/conf.d/default.conf
COPY nginx.conf /etc/nginx/nginx.conf
COPY --from=build /app/out /usr/share/nginx/html

EXPOSE 8080
RUN nginx -t
CMD ["nginx", "-g", "daemon off;"]
