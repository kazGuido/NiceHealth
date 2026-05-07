FROM node:20-bookworm-slim

WORKDIR /app

COPY package.json package-lock.json* ./
RUN npm install --omit=dev

COPY server.js ./

ENV NODE_ENV=production
ENV PORT=8765
ENV AUTH_DIR=/app/auth_info

EXPOSE 8765

CMD ["node", "server.js"]
