FROM node:22-alpine AS build
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .

# Browser keys ship in the bundle by design and are protected by an HTTP
# referrer restriction on the key itself, not by secrecy.
ARG NEXT_PUBLIC_MAPS_API_KEY=""
ENV NEXT_PUBLIC_MAPS_API_KEY=$NEXT_PUBLIC_MAPS_API_KEY
ARG NEXT_PUBLIC_API_URL=""
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL
RUN npm run build

FROM nginx:1.27-alpine
RUN rm -rf /usr/share/nginx/html/* /etc/nginx/conf.d/default.conf
COPY nginx.conf.template /etc/nginx/nginx.conf.template
COPY --from=build /app/out /usr/share/nginx/html

ARG NEXT_PUBLIC_API_URL=""
ENV API_ORIGIN=$NEXT_PUBLIC_API_URL

EXPOSE 8080
CMD ["sh", "-c", "envsubst '${API_ORIGIN}' < /etc/nginx/nginx.conf.template > /etc/nginx/nginx.conf && nginx -t && nginx -g 'daemon off;'"]
