# Day 7：OpenAPI 接口文档

## 今天完成了什么

- 安装 `drf-spectacular`。
- 配置 DRF 使用 spectacular 生成 OpenAPI schema。
- 新增 OpenAPI 原始文档接口：`GET /api/schema/`。
- 新增 Swagger UI 页面：`GET /api/docs/`。
- 新增 ReDoc 页面：`GET /api/redoc/`。
- 为健康检查和工单接口补充 schema 注解。
- 补充接口文档端点测试。

## 三个文档端点的区别

| 路径 | 作用 |
| --- | --- |
| `/api/schema/` | 机器可读的 OpenAPI schema，适合导入 Apifox、Postman 或前端工具 |
| `/api/docs/` | Swagger UI，适合开发阶段在线调试接口 |
| `/api/redoc/` | ReDoc，适合阅读接口说明 |

## 为什么需要接口文档？

接口文档可以让后端接口变得可发现、可调试、可协作。

没有接口文档时，前端或测试同学只能问后端：

- 有哪些接口？
- 请求字段有哪些？
- 响应字段有哪些？
- 哪些接口需要 token？
- 路径参数和查询参数怎么传？

接入 OpenAPI 后，这些信息可以从代码自动生成，减少沟通成本，也减少文档和代码不一致的问题。

## 核心配置

在 `INSTALLED_APPS` 中注册：

```python
'drf_spectacular'
```

在 DRF 配置中指定 schema class：

```python
'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema'
```

在项目路由中暴露文档端点：

```python
path('api/schema/', SpectacularAPIView.as_view(), name='schema')
path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui')
path('api/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc')
```

## 为什么要给自定义接口加注解？

DRF 的 `ModelViewSet` 通常能自动推断接口结构，但自定义 `APIView` 或自定义 action 有时推断不完整。

比如健康检查接口不是基于模型的 CRUD，所以我们用 `@extend_schema` 补充说明：

```python
@extend_schema(
    summary='健康检查',
    description='用于确认 FlowDesk 后端服务是否正常响应。',
)
```

这样生成的接口文档更完整，warning 也更少。

## 核心概念

### 什么是 OpenAPI？

OpenAPI 是一种描述 HTTP API 的规范。它会描述接口路径、请求方法、请求参数、请求体、响应结构和认证方式。

### 什么是 Swagger UI？

Swagger UI 是一个基于 OpenAPI schema 的网页界面。开发者可以在页面上查看接口，也可以直接填写参数发请求。

### 什么是 ReDoc？

ReDoc 也是 OpenAPI 文档页面，但更偏阅读体验，适合给别人浏览接口说明。

### 什么是 schema？

schema 是接口结构描述。对人来说，它可能不如网页直观；但对工具来说，它非常有用，可以导入接口测试工具或生成客户端代码。

## 面试题

1. 为什么后端项目需要接口文档？
2. OpenAPI 是什么？
3. Swagger UI 和 ReDoc 有什么区别？
4. 为什么自动生成文档比手写文档更可靠？
5. drf-spectacular 在 DRF 项目里解决什么问题？
6. 自定义接口为什么有时需要 `extend_schema`？

## 简短回答

1. 接口文档能降低前后端协作成本，让接口字段、路径和认证方式更清楚。
2. OpenAPI 是描述 HTTP API 的标准规范。
3. Swagger UI 更适合调试接口，ReDoc 更适合阅读接口。
4. 自动文档来自代码结构，减少代码改了但文档没更新的问题。
5. drf-spectacular 可以根据 DRF 的 Serializer 和 ViewSet 生成 OpenAPI schema。
6. 自定义接口没有标准模型结构时，工具不一定能完整推断，需要手动补充说明。

## 面试时怎么讲今天的内容

我在 FlowDesk 中接入了 drf-spectacular，用它自动生成 OpenAPI schema，并提供 Swagger UI 和 ReDoc 页面。这样前端或测试人员可以直接查看接口路径、请求字段、响应结构和认证方式。对于健康检查这类自定义接口，我使用 `extend_schema` 补充说明，保证生成的接口文档更完整。
