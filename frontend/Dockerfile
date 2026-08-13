FROM node:20-alpine

WORKDIR /app

# 安装 pnpm（版本由 package.json 的 packageManager 字段指定）
RUN corepack enable && corepack prepare pnpm@10.6.3 --activate

# 复制依赖清单（pnpm-lock.yaml 存在时一并复制）
COPY package.json ./
COPY pnpm-lock.yaml* ./

# 安装依赖
RUN pnpm install

# 复制源码
COPY . .

EXPOSE 5173

CMD ["pnpm", "run", "dev", "--", "--host", "0.0.0.0"]
