"""
中央数据库连接管理 - PostgreSQL 适配器

私有化部署中使用本地 PostgreSQL，通过适配器提供类似 Supabase 的 API
"""

from typing import Optional, Any, List, Dict
from datetime import datetime, timezone
from core.utils.logger import logger
from core.services.postgres import PostgresConnection
import threading
import json


class PostgresQueryResult:
    """PostgreSQL 查询结果，模拟 Supabase 返回格式"""
    def __init__(self, data: List[Any] = None, count: int = 0):
        self.data = data or []
        self.count = count


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
    
    def __init__(self, pool, table_name: str):
        self._pool = pool
        self._table_name = table_name
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
        
        for op, column, value in self._filters:
            if op == 'eq':
                conditions.append(f'"{column}" = ${param_idx}')
                params.append(value)
                param_idx += 1
            elif op == 'neq':
                conditions.append(f'"{column}" != ${param_idx}')
                params.append(value)
                param_idx += 1
            elif op == 'gt':
                conditions.append(f'"{column}" > ${param_idx}')
                params.append(value)
                param_idx += 1
            elif op == 'gte':
                conditions.append(f'"{column}" >= ${param_idx}')
                params.append(value)
                param_idx += 1
            elif op == 'lt':
                conditions.append(f'"{column}" < ${param_idx}')
                params.append(value)
                param_idx += 1
            elif op == 'lte':
                conditions.append(f'"{column}" <= ${param_idx}')
                params.append(value)
                param_idx += 1
            elif op == 'like':
                conditions.append(f'"{column}" LIKE ${param_idx}')
                params.append(value)
                param_idx += 1
            elif op == 'ilike':
                conditions.append(f'"{column}" ILIKE ${param_idx}')
                params.append(value)
                param_idx += 1
            elif op == 'is':
                if value is None:
                    conditions.append(f'"{column}" IS NULL')
                else:
                    conditions.append(f'"{column}" IS ${param_idx}')
                    params.append(value)
                    param_idx += 1
            elif op == 'is_not':
                if value is None:
                    conditions.append(f'"{column}" IS NOT NULL')
                else:
                    conditions.append(f'"{column}" IS NOT ${param_idx}')
                    params.append(value)
                    param_idx += 1
            elif op == 'not_in':
                if value:
                    placeholders = ', '.join(f'${i}' for i in range(param_idx, param_idx + len(value)))
                    conditions.append(f'"{column}" NOT IN ({placeholders})')
                    params.extend(value)
                    param_idx += len(value)
                else:
                    conditions.append('TRUE')  # Empty NOT IN clause
            elif op == 'in':
                if value:
                    placeholders = ', '.join(f'${i}' for i in range(param_idx, param_idx + len(value)))
                    conditions.append(f'"{column}" IN ({placeholders})')
                    params.extend(value)
                    param_idx += len(value)
                else:
                    conditions.append('FALSE')  # Empty IN clause
            elif op == 'contains':
                conditions.append(f'"{column}" @> ${param_idx}')
                params.append(json.dumps(value) if not isinstance(value, str) else value)
                param_idx += 1
            elif op == 'contained_by':
                conditions.append(f'"{column}" <@ ${param_idx}')
                params.append(json.dumps(value) if not isinstance(value, str) else value)
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
        
        # 构建基础查询
        query = f'SELECT {fields} FROM "{self._table_name}"{where_clause}'
        
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
            count_query = f'SELECT COUNT(*) FROM "{self._table_name}"{where_clause}'
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
                    processed_values.append(json.dumps(v))
                elif isinstance(v, datetime):
                    # 确保 datetime 是 offset-aware 的 UTC 时间
                    if v.tzinfo is None:
                        # 如果是 offset-naive，假设它是 UTC 时间
                        v = v.replace(tzinfo=timezone.utc)
                    # 转换为 UTC 时间（如果已经是 offset-aware）
                    v = v.astimezone(timezone.utc)
                    processed_values.append(v)
                else:
                    processed_values.append(v)
            
            col_names = ', '.join(f'"{c}"' for c in columns)
            placeholders = ', '.join(f'${i+1}' for i in range(len(columns)))
            
            query = f'INSERT INTO "{self._table_name}" ({col_names}) VALUES ({placeholders})'
            if self._returning:
                query += ' RETURNING *'
            
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
            set_parts.append(f'"{key}" = ${param_idx}')
            if isinstance(value, (dict, list)):
                set_params.append(json.dumps(value))
            else:
                set_params.append(value)
            param_idx += 1
        
        query = f'UPDATE "{self._table_name}" SET {", ".join(set_parts)}{where_clause}'
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
        
        query = f'DELETE FROM "{self._table_name}"{where_clause}'
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
            
            # 处理 JSON 字段
            processed_values = []
            for v in values:
                if isinstance(v, (dict, list)):
                    processed_values.append(json.dumps(v))
                else:
                    processed_values.append(v)
            
            col_names = ', '.join(f'"{c}"' for c in columns)
            placeholders = ', '.join(f'${i+1}' for i in range(len(columns)))
            
            # 假设第一个字段是主键
            pk = columns[0]
            update_parts = ', '.join(f'"{c}" = EXCLUDED."{c}"' for c in columns[1:])
            
            query = f'''
                INSERT INTO "{self._table_name}" ({col_names}) 
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


class PostgresClient:
    """PostgreSQL 客户端 - 提供类似 Supabase 的 API"""
    
    def __init__(self, pool):
        self._pool = pool
    
    def table(self, table_name: str) -> PostgresQueryBuilder:
        """返回查询构建器"""
        return PostgresQueryBuilder(self._pool, table_name)
    
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
