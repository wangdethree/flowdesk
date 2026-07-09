# Day 2：用户注册与 JWT 登录

## 今天完成了什么

- 新增用户注册接口：`POST /api/users/register/`。
- 接入 SimpleJWT 登录接口：`POST /api/users/login/`。
- 接入 token 刷新接口：`POST /api/users/token/refresh/`。
- 新增当前用户信息接口：`GET /api/users/me/`。
- 补充用户认证接口测试。

## 接口清单

### 注册

请求：

```http
POST /api/users/register/
Content-Type: application/json
```

```json
{
  "username": "alice",
  "email": "alice@example.com",
  "password": "TestPass123",
  "password_confirm": "TestPass123"
}
```

返回：

```json
{
  "id": 1,
  "username": "alice",
  "email": "alice@example.com"
}
```

### 登录

请求：

```http
POST /api/users/login/
Content-Type: application/json
```

```json
{
  "username": "alice",
  "password": "TestPass123"
}
```

返回：

```json
{
  "refresh": "...",
  "access": "..."
}
```

### 当前用户

请求：

```http
GET /api/users/me/
Authorization: Bearer <access_token>
```

返回：

```json
{
  "id": 1,
  "username": "alice",
  "email": "alice@example.com",
  "first_name": "",
  "last_name": "",
  "date_joined": "2026-07-09T..."
}
```

## 需要理解的文件

`apps/users/serializers.py`

负责用户注册参数校验、密码确认、密码强度校验和用户创建。Serializer 可以理解为接口数据的“入口检查员”。

`apps/users/views.py`

负责注册接口和当前用户信息接口。View 处理请求，并决定使用哪个 Serializer 返回响应。

`apps/users/urls.py`

负责用户模块的路由，把注册、登录、刷新 token、当前用户信息接口挂到 `/api/users/` 下。

`apps/users/tests.py`

负责验证用户认证链路是否可用，包括注册、登录、未登录拦截、带 token 访问当前用户信息。

## 核心概念

### 什么是认证？

认证是确认“你是谁”。比如用户提交用户名和密码，后端校验成功后发放 token。

### 什么是鉴权？

鉴权是判断“你有没有权限做这件事”。比如普通用户只能看自己的工单，管理员可以看全部工单。

### 什么是 JWT？

JWT 是一种携带用户身份信息的 token。登录成功后，后端返回 access token 和 refresh token。客户端后续请求接口时，在请求头里带上 access token，后端就能识别当前用户。

### access token 和 refresh token 有什么区别？

access token 用来访问接口，有效期通常较短。refresh token 用来换新的 access token，有效期通常更长。

### 为什么密码不能明文存储？

如果数据库泄露，明文密码会直接暴露用户账号风险。Django 的 `create_user` 会对密码做哈希处理，数据库里保存的是哈希值，不是原始密码。

### Serializer 的作用是什么？

Serializer 主要负责三件事：校验请求数据、把模型对象转换成 JSON、把合法数据保存成模型对象。

## 面试题

1. 认证和鉴权有什么区别？
2. JWT 登录流程是什么？
3. access token 和 refresh token 有什么区别？
4. 为什么密码不能明文存储？
5. Django 的 `create_user` 和 `create` 有什么区别？
6. DRF Serializer 主要解决什么问题？
7. 为什么需要 `/me/` 这种当前用户接口？

## 简短回答

1. 认证解决“你是谁”，鉴权解决“你能不能做”。
2. 用户提交用户名密码，后端校验成功后签发 token，客户端后续请求携带 token。
3. access token 用于访问接口，有效期短；refresh token 用于刷新 access token，有效期长。
4. 明文密码泄露风险极高，应该保存不可逆的哈希值。
5. `create_user` 会处理密码哈希，`create` 只是普通创建对象。
6. Serializer 用于校验输入、序列化输出和保存模型。
7. `/me/` 可以让前端根据 token 获取当前登录用户的信息。

## 面试时怎么讲今天的内容

我在 FlowDesk 中实现了用户注册和 JWT 登录。注册时使用 DRF Serializer 校验用户名、邮箱、密码和确认密码，并通过 Django 的 `create_user` 保存哈希后的密码。登录部分复用 SimpleJWT，返回 access token 和 refresh token。后续接口通过 `Authorization: Bearer <token>` 识别当前用户，并提供 `/api/users/me/` 接口返回当前登录用户信息。
