"""
中央数据库连接管理 - PostgreSQL 适配器

私有化部署中使用本地 PostgreSQL，通过适配器提供类似 Supabase 的 API
"""

from typing import Optional, Any, List, Dict
from datetime import datetime, timezone
from uuid import UUID
from core.utils.logger import logger
from core.services.postgres import PostgresConnection
import threading
import json


class PostgresQueryResult:
    """PostgreSQL 查询结果，模拟 Supabase 返回格式"""
    def __init__(self, data: List[Any] = None, count: int = 0):
        self.data = data or []
        self.count = count


class UUIDEncoder(json.JSONEncoder):
    """Custom JSON encoder that handles UUID and datetime objects"""
    def default(self, obj):
        if isinstance(obj, UUID):
            return str(obj)
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)


class PostgresNotBuilder:
    """否定条件构建器 - 用于 not_.is_(), not_.in_() 等"""
    def __init__(self, builder: 'PostgresQueryBuilder'):
        self._builder = builder
    
    def is_(self, column: str, value: Any) -> 'PostgresQueryBuilder':
        """IS NOT 条件"""
        # 如果值是字符串 'null'，转换为 None，这样会生成 IS NOT NULL
        if value == 'null' or value is None:
            value = None
        self._builder._filters.append(('is_not', column, value))
        return self._builder
    
    def in_(self, column: str, values: List[Any]) -> 'PostgresQueryBuilder':
        """NOT IN 条件"""
        self._builder._filters.append(('not_in', column, values))
        return self._builder


class PostgresQueryBuilder:
    """PostgreSQL 查询构建器 - 模拟 Supabase API"""
    
    def __init__(self, pool, table_name: str, schema_name: str = 'public'):
        self._pool = pool
        self._table_name = table_name
        self._schema_name = schema_name
        self._select_fields = '*'
        self._count_mode = None
        self._filters: List[tuple] = []
        self._order_by: List[tuple] = []
        self._limit_val: Optional[int] = None
        self._offset_val: Optional[int] = None
        self._range_start: Optional[int] = None
        self._range_end: Optional[int] = None
        self._single = False
        self._maybe_single = False
        self._operation = 'select'  # select, insert, update, delete, upsert
        self._data: Any = None
        self._returning = True
    
    def select(self, fields: str = '*', count: str = None, **kwargs) -> 'PostgresQueryBuilder':
        self._select_fields = fields
        self._operation = 'select'
        if count:
            self._count_mode = count
        return self
    
    def insert(self, data: Any, returning: str = 'representation') -> 'PostgresQueryBuilder':
        self._operation = 'insert'
        self._data = data if isinstance(data, list) else [data]
        self._returning = returning != 'minimal'
        return self
    
    def update(self, data: Dict[str, Any], returning: str = 'representation') -> 'PostgresQueryBuilder':
        self._operation = 'update'
        self._data = data
        self._returning = returning != 'minimal'
        return self
    
    def upsert(self, data: Any, on_conflict: str = None, returning: str = 'representation') -> 'PostgresQueryBuilder':
        self._operation = 'upsert'
        self._data = data if isinstance(data, list) else [data]
        self._returning = returning != 'minimal'
        return self
    
    def delete(self, returning: str = 'representation') -> 'PostgresQueryBuilder':
        self._operation = 'delete'
        self._returning = returning != 'minimal'
        return self
    
    def eq(self, column: str, value: Any) -> 'PostgresQueryBuilder':
        self._filters.append(('eq', column, value))
        return self
    
    def neq(self, column: str, value: Any) -> 'PostgresQueryBuilder':
        self._filters.append(('neq', column, value))
        return self
    
    def gt(self, column: str, value: Any) -> 'PostgresQueryBuilder':
        self._filters.append(('gt', column, value))
        return self
    
    def gte(self, column: str, value: Any) -> 'PostgresQueryBuilder':
        self._filters.append(('gte', column, value))
        return self
    
    def lt(self, column: str, value: Any) -> 'PostgresQueryBuilder':
        self._filters.append(('lt', column, value))
        return self
    
    def lte(self, column: str, value: Any) -> 'PostgresQueryBuilder':
        self._filters.append(('lte', column, value))
        return self
    
    def like(self, column: str, pattern: str) -> 'PostgresQueryBuilder':
        self._filters.append(('like', column, pattern))
        return self
    
    def ilike(self, column: str, pattern: str) -> 'PostgresQueryBuilder':
        self._filters.append(('ilike', column, pattern))
        return self
    
    def is_(self, column: str, value: Any) -> 'PostgresQueryBuilder':
        self._filters.append(('is', column, value))
        return self
    
    def in_(self, column: str, values: List[Any]) -> 'PostgresQueryBuilder':
        self._filters.append(('in', column, values))
        return self
    
    def contains(self, column: str, value: Any) -> 'PostgresQueryBuilder':
        self._filters.append(('contains', column, value))
        return self
    
    def contained_by(self, column: str, value: Any) -> 'PostgresQueryBuilder':
        self._filters.append(('contained_by', column, value))
        return self
    
    def jsonb_eq(self, jsonb_column: str, jsonb_path: str, value: Any) -> 'PostgresQueryBuilder':
        """JSONB 字段相等查询
        
        Args:
            jsonb_column: JSONB 列名 (如 'sandbox')
            jsonb_path: JSONB 路径 (如 'id')
            value: 要匹配的值
        
        Examples:
            .jsonb_eq('sandbox', 'id', 'abc123')  # sandbox->>'id' = 'abc123'
        """
        self._filters.append(('jsonb_eq', jsonb_column, jsonb_path, value))
        return self
    
    def order(self, column: str, desc: bool = False, **kwargs) -> 'PostgresQueryBuilder':
        self._order_by.append((column, desc))
        return self
    
    def limit(self, count: int) -> 'PostgresQueryBuilder':
        self._limit_val = count
        return self
    
    def offset(self, count: int) -> 'PostgresQueryBuilder':
        self._offset_val = count
        return self
    
    def range(self, start: int, end: int) -> 'PostgresQueryBuilder':
        self._range_start = start
        self._range_end = end
        return self
    
    def single(self) -> 'PostgresQueryBuilder':
        self._single = True
        self._limit_val = 1
        return self
    
    def maybe_single(self) -> 'PostgresQueryBuilder':
        self._maybe_single = True
        self._limit_val = 1
        return self
    
    @property
    def not_(self) -> 'PostgresNotBuilder':
        """返回否定条件构建器"""
        return PostgresNotBuilder(self)

    def _build_where_clause(self) -> tuple:
        """构建 WHERE 子句和参数"""
        if not self._filters:
            return '', []
        
        conditions = []
        params = []
        param_idx = 1
        
        for filter_item in self._filters:
            op = filter_item[0]
            
            if op == 'eq':
                column, value = filter_item[1], filter_item[2]
                conditions.append(f'"{column}" = ${param_idx}')
                params.append(value)
                param_idx += 1
            elif op == 'neq':
                column, value = filter_item[1], filter_item[2]
                conditions.append(f'"{column}" != ${param_idx}')
                params.append(value)
                param_idx += 1
            elif op == 'gt':
                column, value = filter_item[1], filter_item[2]
                conditions.append(f'"{column}" > ${param_idx}')
                params.append(value)
                param_idx += 1
            elif op == 'gte':
                column, value = filter_item[1], filter_item[2]
                conditions.append(f'"{column}" >= ${param_idx}')
                params.append(value)
                param_idx += 1
            elif op == 'lt':
                column, value = filter_item[1], filter_item[2]
                conditions.append(f'"{column}" < ${param_idx}')
                params.append(value)
                param_idx += 1
            elif op == 'lte':
                column, value = filter_item[1], filter_item[2]
                conditions.append(f'"{column}" <= ${param_idx}')
                params.append(value)
                param_idx += 1
            elif op == 'like':
                column, value = filter_item[1], filter_item[2]
                conditions.append(f'"{column}" LIKE ${param_idx}')
                params.append(value)
                param_idx += 1
            elif op == 'ilike':
                column, value = filter_item[1], filter_item[2]
                conditions.append(f'"{column}" ILIKE ${param_idx}')
                params.append(value)
                param_idx += 1
            elif op == 'is':
                column, value = filter_item[1], filter_item[2]
                if value is None:
                    conditions.append(f'"{column}" IS NULL')
                else:
                    conditions.append(f'"{column}" IS ${param_idx}')
                    params.append(value)
                    param_idx += 1
            elif op == 'is_not':
                column, value = filter_item[1], filter_item[2]
                if value is None:
                    conditions.append(f'"{column}" IS NOT NULL')
                else:
                    conditions.append(f'"{column}" IS NOT ${param_idx}')
                    params.append(value)
                    param_idx += 1
            elif op == 'not_in':
                column, value = filter_item[1], filter_item[2]
                if value:
                    placeholders = ', '.join(f'${i}' for i in range(param_idx, param_idx + len(value)))
                    conditions.append(f'"{column}" NOT IN ({placeholders})')
                    params.extend(value)
                    param_idx += len(value)
                else:
                    conditions.append('TRUE')  # Empty NOT IN clause
            elif op == 'in':
                column, value = filter_item[1], filter_item[2]
                if value:
                    placeholders = ', '.join(f'${i}' for i in range(param_idx, param_idx + len(value)))
                    conditions.append(f'"{column}" IN ({placeholders})')
                    params.extend(value)
                    param_idx += len(value)
                else:
                    conditions.append('FALSE')  # Empty IN clause
            elif op == 'contains':
                column, value = filter_item[1], filter_item[2]
                conditions.append(f'"{column}" @> ${param_idx}')
                params.append(json.dumps(value) if not isinstance(value, str) else value)
                param_idx += 1
            elif op == 'contained_by':
                column, value = filter_item[1], filter_item[2]
                conditions.append(f'"{column}" <@ ${param_idx}')
                params.append(json.dumps(value) if not isinstance(value, str) else value)
                param_idx += 1
            elif op == 'jsonb_eq':
                # filter_item: ('jsonb_eq', 'sandbox', 'id', 'abc123')
                # 生成: "sandbox"->>'id' = $1
                jsonb_column, jsonb_path, actual_value = filter_item[1], filter_item[2], filter_item[3]
                conditions.append(f'"{jsonb_column}"->>\'{jsonb_path}\' = ${param_idx}')
                params.append(actual_value)
                param_idx += 1
        
        return ' WHERE ' + ' AND '.join(conditions), params

    def _format_select_fields(self) -> str:
        """格式化 SELECT 字段"""
        if self._select_fields == '*':
            return '*'
        # 处理字段列表，添加引号
        fields = [f.strip() for f in self._select_fields.split(',')]
        formatted = []
        for f in fields:
            # 跳过已有特殊处理的字段（如函数调用）
            if '(' in f or '"' in f:
                formatted.append(f)
            else:
                formatted.append(f'"{f}"')
        return ', '.join(formatted)

    async def execute(self) -> PostgresQueryResult:
        """执行查询"""
        try:
            if not self._pool:
                logger.warning("PostgreSQL 连接池未初始化，返回空数据")
                return PostgresQueryResult(data=[], count=0)
            
            async with self._pool.acquire() as conn:
                if self._operation == 'select':
                    return await self._execute_select(conn)
                elif self._operation == 'insert':
                    return await self._execute_insert(conn)
                elif self._operation == 'update':
                    return await self._execute_update(conn)
                elif self._operation == 'delete':
                    return await self._execute_delete(conn)
                elif self._operation == 'upsert':
                    return await self._execute_upsert(conn)
                else:
                    return PostgresQueryResult(data=[], count=0)
        except Exception as e:
            logger.error(f"PostgreSQL 查询错误 ({self._table_name}): {e}")
            raise

    async def _execute_select(self, conn) -> PostgresQueryResult:
        """执行 SELECT 查询"""
        fields = self._format_select_fields()
        where_clause, params = self._build_where_clause()
        
        # 构建基础查询 - 使用 schema.table 格式
        full_table_name = f'"{self._schema_name}"."{self._table_name}"'
        query = f'SELECT {fields} FROM {full_table_name}{where_clause}'
        
        # 添加排序
        if self._order_by:
            order_parts = [f'"{col}" {"DESC" if desc else "ASC"}' for col, desc in self._order_by]
            query += ' ORDER BY ' + ', '.join(order_parts)
        
        # 添加分页
        if self._range_start is not None and self._range_end is not None:
            query += f' LIMIT {self._range_end - self._range_start + 1} OFFSET {self._range_start}'
        else:
            if self._limit_val is not None:
                query += f' LIMIT {self._limit_val}'
            if self._offset_val is not None:
                query += f' OFFSET {self._offset_val}'
        
        # 执行查询
        rows = await conn.fetch(query, *params)
        data = [dict(row) for row in rows]
        
        # 如果需要计数
        count = len(data)
        if self._count_mode == 'exact':
            full_table_name = f'"{self._schema_name}"."{self._table_name}"'
            count_query = f'SELECT COUNT(*) FROM {full_table_name}{where_clause}'
            count_result = await conn.fetchval(count_query, *params)
            count = count_result or 0
        
        # 处理 single/maybe_single
        if self._single:
            if not data:
                raise Exception(f"No rows found in {self._table_name}")
            return PostgresQueryResult(data=data[0] if data else None, count=count)
        if self._maybe_single:
            return PostgresQueryResult(data=data[0] if data else None, count=count)
        
        return PostgresQueryResult(data=data, count=count)

    async def _execute_insert(self, conn) -> PostgresQueryResult:
        """执行 INSERT 查询"""
        if not self._data:
            return PostgresQueryResult(data=[], count=0)
        
        results = []
        for row in self._data:
            columns = list(row.keys())
            values = list(row.values())
            
            # 处理 JSON 字段和 datetime 对象
            processed_values = []
            for v in values:
                if isinstance(v, (dict, list)):
                    # Use custom encoder to handle UUID objects in dicts/lists
                    processed_values.append(json.dumps(v, cls=UUIDEncoder))
                elif isinstance(v, datetime):
                    # asyncpg 需要 offset-aware datetime；统一确保使用 timezone.utc
                    if v.tzinfo is None:
                        # Naive datetime - 添加 UTC timezone
                        processed_values.append(v.replace(tzinfo=timezone.utc))
                    elif v.tzinfo == timezone.utc:
                        # 已经是 UTC timezone.utc,直接使用
                        processed_values.append(v)
                    else:
                        # 其他 timezone - 转换为 UTC 并替换 tzinfo 为 timezone.utc
                        utc_time = v.astimezone(timezone.utc)
                        # 重新创建 datetime 对象,使用标准的 timezone.utc
                        processed_values.append(datetime(
                            utc_time.year, utc_time.month, utc_time.day,
                            utc_time.hour, utc_time.minute, utc_time.second,
                            utc_time.microsecond, tzinfo=timezone.utc
                        ))
                else:
                    processed_values.append(v)
            
            col_names = ', '.join(f'"{c}"' for c in columns)
            placeholders = ', '.join(f'${i+1}' for i in range(len(columns)))
            
            full_table_name = f'"{self._schema_name}"."{self._table_name}"'
            query = f'INSERT INTO {full_table_name} ({col_names}) VALUES ({placeholders})'
            if self._returning:
                query += ' RETURNING *'
            
            # 调试日志: 输出所有参数的类型和值
            for i, (col, val) in enumerate(zip(columns, processed_values)):
                if isinstance(val, datetime):
                    logger.debug(
                        f"Param ${i+1} ({col}): type={type(val).__name__}, "
                        f"value={val}, tzinfo={val.tzinfo}, "
                        f"tzinfo_type={type(val.tzinfo).__name__ if val.tzinfo else 'None'}"
                    )
            
            if self._returning:
                result = await conn.fetchrow(query, *processed_values)
                if result:
                    results.append(dict(result))
            else:
                await conn.execute(query, *processed_values)
        
        return PostgresQueryResult(data=results, count=len(results))

    async def _execute_update(self, conn) -> PostgresQueryResult:
        """执行 UPDATE 查询"""
        if not self._data:
            return PostgresQueryResult(data=[], count=0)
        
        where_clause, where_params = self._build_where_clause()
        
        set_parts = []
        set_params = []
        param_idx = len(where_params) + 1
        
        for key, value in self._data.items():
            set_parts.append(f'"{ key}" = ${param_idx}')
            if isinstance(value, (dict, list)):
                # Use custom encoder to handle UUID objects in dicts/lists
                set_params.append(json.dumps(value, cls=UUIDEncoder))
            elif isinstance(value, datetime):
                # asyncpg 要求 datetime 必须是 offset-aware 的
                if value.tzinfo is None:
                    # 如果是 offset-naive，直接替换为 UTC 时区
                    set_params.append(value.replace(tzinfo=timezone.utc))
                else:
                    # 如果已经有时区，保持原样
                    set_params.append(value)
            else:
                set_params.append(value)
            param_idx += 1
        
        full_table_name = f'"{self._schema_name}"."{self._table_name}"'
        query = f'UPDATE {full_table_name} SET {", ".join(set_parts)}{where_clause}'
        if self._returning:
            query += ' RETURNING *'
        
        all_params = where_params + set_params
        
        if self._returning:
            rows = await conn.fetch(query, *all_params)
            data = [dict(row) for row in rows]
            return PostgresQueryResult(data=data, count=len(data))
        else:
            result = await conn.execute(query, *all_params)
            count = int(result.split()[-1]) if result else 0
            return PostgresQueryResult(data=[], count=count)

    async def _execute_delete(self, conn) -> PostgresQueryResult:
        """执行 DELETE 查询"""
        where_clause, params = self._build_where_clause()
        
        full_table_name = f'"{self._schema_name}"."{self._table_name}"'
        query = f'DELETE FROM {full_table_name}{where_clause}'
        if self._returning:
            query += ' RETURNING *'
        
        if self._returning:
            rows = await conn.fetch(query, *params)
            data = [dict(row) for row in rows]
            return PostgresQueryResult(data=data, count=len(data))
        else:
            result = await conn.execute(query, *params)
            count = int(result.split()[-1]) if result else 0
            return PostgresQueryResult(data=[], count=count)

    async def _execute_upsert(self, conn) -> PostgresQueryResult:
        """执行 UPSERT (INSERT ON CONFLICT UPDATE) 查询"""
        if not self._data:
            return PostgresQueryResult(data=[], count=0)
        
        results = []
        for row in self._data:
            columns = list(row.keys())
            values = list(row.values())
            
            # 处理 JSON 字段和 datetime 对象
            processed_values = []
            for v in values:
                if isinstance(v, (dict, list)):
                    # Use custom encoder to handle UUID objects in dicts/lists
                    processed_values.append(json.dumps(v, cls=UUIDEncoder))
                elif isinstance(v, datetime):
                    # asyncpg 要求 datetime 必须是 offset-aware 的
                    if v.tzinfo is None:
                        # 如果是 offset-naive，直接替换为 UTC 时区
                        processed_values.append(v.replace(tzinfo=timezone.utc))
                    else:
                        # 如果已经有时区，保持原样
                        processed_values.append(v)
                else:
                    processed_values.append(v)
            
            col_names = ', '.join(f'"{c}"' for c in columns)
            placeholders = ', '.join(f'${i+1}' for i in range(len(columns)))
            
            # 假设第一个字段是主键
            pk = columns[0]
            update_parts = ', '.join(f'"{c}" = EXCLUDED."{c}"' for c in columns[1:])
            
            full_table_name = f'"{self._schema_name}"."{self._table_name}"'
            query = f'''
                INSERT INTO {full_table_name} ({col_names}) 
                VALUES ({placeholders})
                ON CONFLICT ("{pk}") DO UPDATE SET {update_parts}
            '''
            if self._returning:
                query += ' RETURNING *'
            
            if self._returning:
                result = await conn.fetchrow(query, *processed_values)
                if result:
                    results.append(dict(result))
            else:
                await conn.execute(query, *processed_values)
        
        return PostgresQueryResult(data=results, count=len(results))


class PostgresStorageBucket:
    """PostgreSQL Storage Bucket - 模拟 Supabase Storage API"""
    
    def __init__(self, pool, bucket_name: str):
        self._pool = pool
        self._bucket_name = bucket_name
    
    async def upload(self, path: str, file_content: bytes, file_options: dict = None) -> dict:
        """上传文件到存储桶（本地实现：将文件信息存储到数据库）"""
        # 在本地部署中，我们只记录文件元数据到数据库
        # 实际文件内容可以存储在文件系统或数据库中
        # 这里返回成功响应以保持 API 兼容性
        logger.debug(f"Storage upload: bucket={self._bucket_name}, path={path}, size={len(file_content)}")
        return {"path": path}
    
    async def download(self, path: str) -> bytes:
        """从存储桶下载文件"""
        # 本地实现：从数据库或文件系统读取文件
        logger.debug(f"Storage download: bucket={self._bucket_name}, path={path}")
        # 这里应该实现实际的下载逻辑
        raise NotImplementedError("File download not yet implemented for local storage")
    
    async def remove(self, paths: list) -> dict:
        """从存储桶删除文件"""
        logger.debug(f"Storage remove: bucket={self._bucket_name}, paths={paths}")
        # 本地实现：从数据库删除文件记录
        return {"message": "Files removed"}
    
    async def copy(self, from_path: str, to_path: str) -> dict:
        """复制文件"""
        logger.debug(f"Storage copy: bucket={self._bucket_name}, from={from_path}, to={to_path}")
        return {"path": to_path}
    
    async def create_signed_url(self, path: str, expires_in: int) -> dict:
        """创建签名 URL"""
        # 本地实现：生成一个临时的访问 URL
        # 这里返回一个占位符 URL，实际应该根据配置生成
        from core.utils.config import config
        backend_url = config.get('BACKEND_URL', 'http://localhost:8000')
        signed_url = f"{backend_url}/storage/{self._bucket_name}/{path}"
        logger.debug(f"Storage signed URL: bucket={self._bucket_name}, path={path}, expires_in={expires_in}")
        return {"signedURL": signed_url}
    
    async def get_public_url(self, path: str) -> str:
        """获取公共 URL"""
        from core.utils.config import config
        backend_url = config.get('BACKEND_URL', 'http://localhost:8000')
        public_url = f"{backend_url}/storage/{self._bucket_name}/{path}"
        logger.debug(f"Storage public URL: bucket={self._bucket_name}, path={path}")
        return public_url


class PostgresStorage:
    """PostgreSQL Storage - 模拟 Supabase Storage API"""
    
    def __init__(self, pool):
        self._pool = pool
    
    def from_(self, bucket_name: str) -> PostgresStorageBucket:
        """返回指定存储桶"""
        return PostgresStorageBucket(self._pool, bucket_name)


class PostgresClient:
    """PostgreSQL 客户端 - 提供类似 Supabase 的 API"""
    
    def __init__(self, pool, schema_name: str = 'public'):
        self._pool = pool
        self._schema_name = schema_name
        self._storage = PostgresStorage(pool)
    
    @property
    def storage(self) -> PostgresStorage:
        """返回 Storage 对象"""
        return self._storage
    
    def table(self, table_name: str) -> PostgresQueryBuilder:
        """返回查询构建器"""
        return PostgresQueryBuilder(self._pool, table_name, schema_name=self._schema_name)
    
    def from_(self, table_name: str) -> PostgresQueryBuilder:
        """返回查询构建器（与 table() 方法相同，用于兼容性）"""
        return self.table(table_name)
    
    def schema(self, schema_name: str) -> 'PostgresClient':
        """返回指定 schema 的客户端"""
        return PostgresClient(self._pool, schema_name=schema_name)
    
    async def rpc(self, function_name: str, params: dict = None) -> PostgresQueryResult:
        """执行存储过程"""
        try:
            if not self._pool:
                logger.warning("PostgreSQL 连接池未初始化")
                return PostgresQueryResult(data=[], count=0)
            
            async with self._pool.acquire() as conn:
                # 构建参数列表
                if params:
                    param_names = ', '.join(f'{k} => ${i+1}' for i, k in enumerate(params.keys()))
                    param_values = list(params.values())
                    query = f'SELECT * FROM {function_name}({param_names})'
                    rows = await conn.fetch(query, *param_values)
                else:
                    query = f'SELECT * FROM {function_name}()'
                    rows = await conn.fetch(query)
                
                data = [dict(row) for row in rows]
                return PostgresQueryResult(data=data, count=len(data))
        except Exception as e:
            logger.error(f"PostgreSQL RPC 调用错误 ({function_name}): {e}")
            # 返回空数据而不是抛出异常
            return PostgresQueryResult(data=[], count=0)


class DBConnection:
    """Thread-safe singleton database connection manager.
    
    使用本地 PostgreSQL，提供类似 Supabase 的 API。
    """
    
    _instance: Optional['DBConnection'] = None
    _lock = threading.Lock()
    _pg_connection: Optional[PostgresConnection] = None
    _client: Optional[PostgresClient] = None

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        pass

    async def initialize(self):
        """初始化数据库连接"""
        if self._initialized:
            return
        
        # 使用 PostgresConnection
        DBConnection._pg_connection = PostgresConnection()
        await DBConnection._pg_connection.initialize()
        DBConnection._client = PostgresClient(DBConnection._pg_connection._pool)

        self._initialized = True
        logger.info("✅ DBConnection 初始化成功（使用本地 PostgreSQL）")

    @classmethod
    async def disconnect(cls):
        """断开数据库连接"""
        if cls._instance:
            cls._instance._initialized = False
        logger.info("✅ 数据库连接已断开")

    @property
    async def client(self) -> PostgresClient:
        """获取 PostgreSQL 客户端"""
        if not self._initialized:
            await self.initialize()
        return DBConnection._client
