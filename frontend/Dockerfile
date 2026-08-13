FROM node:20-alpine

WORKDIR /app

# 安装 pnpm
RUN corepack enable

# 复制依赖清单
COPY package.json pnpm-lock.yaml* ./

# 安装依赖
RUN pnpm install

# 复制源码
COPY . .

EXPOSE 5173

CMD ["pnpm", "run", "dev", "--", "--host", "0.0.0.0"]
