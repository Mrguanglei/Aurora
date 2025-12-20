import httpx
from dotenv import load_dotenv
from core.agentpress.tool import Tool, ToolResult, openapi_schema, tool_metadata
from core.utils.config import config
from core.sandbox.tool_base import SandboxToolsBase
from core.agentpress.thread_manager import ThreadManager
import json
import datetime
import asyncio
import logging
import time
from typing import Optional
from urllib.parse import urlparse
import re

# TODO: add subpages, etc... in filters as sometimes its necessary 

class QuarkSearch:
    """Local Quark search engine implementation"""
    
    # 需要过滤的域名列表
    FILTERED_DOMAINS = {
        'baijiahao.baidu.com',  # 百家号 - 内容质量不稳定
        # 'zhihu.com',         # 知乎需要登录
        # 'zhuanlan.zhihu.com',# 知乎专栏
        # 'juejin.cn',         # 掘金需要登录
        # 'jianshu.com',       # 简书需要登录
        # 'csdn.net',          # CSDN需要登录
        # 'blog.csdn.net',     # CSDN博客
        # 'weibo.com',         # 微博需要登录
        # 'douban.com',        # 豆瓣需要登录
        # 'segmentfault.com',  # 思否需要登录
    }
    
    def __init__(self, base_url: str = "http://192.168.1.204:9018/search"):
        if not base_url:
            raise ValueError("base_url cannot be None or empty")
        self.base_url = base_url
        logging.info(f"QuarkSearch initialized with base_url: {self.base_url}")
    
    def _clean_text(self, text: str) -> str:
        """Clean text by removing problematic characters and normalizing whitespace"""
        if not text:
            return ""
        # 移除HTML标签
        text = re.sub(r'<[^>]+>', '', text)
        # 移除多余的空白字符
        text = re.sub(r'\s+', ' ', text)
        # 保留 Markdown 相关字符，同时移除其他特殊字符
        text = re.sub(r'[^\w\s\-.,?!()[\]{}\'\"#*`~>+=/@|]+', '', text)
        # 移除控制字符，但保留换行和制表符
        text = ''.join(char for char in text if ord(char) >= 32 or char in '\n\t')
        # 规范化 Markdown 语法
        text = re.sub(r'(\*{2,})', '**', text)  # 规范化加粗
        text = re.sub(r'(_{2,})', '__', text)   # 规范化下划线
        text = re.sub(r'(`{3,})', '```', text)  # 规范化代码块
        return text.strip()
    
    def _is_allowed_domain(self, url: str) -> bool:
        """Check if the domain is allowed (not in filtered list)"""
        try:
            domain = urlparse(url).netloc.lower()
            # 移除www.前缀再判断
            if domain.startswith('www.'):
                domain = domain[4:]
            return not any(filtered_domain in domain for filtered_domain in self.FILTERED_DOMAINS)
        except:
            return False
    
    async def search(
        self, 
        query: str, 
        date_range: Optional[str] = None,
        max_results: int = 5,
        snippet_length: int = 1000
    ) -> dict:
        """Search using Quark API and return results in Tavily-compatible format"""
        if not self.base_url:
            error_msg = "QuarkSearch base_url is not configured"
            logging.error(error_msg)
            return {
                "success": False,
                "results": [],
                "answer": "",
                "images": [],
                "response": {},
                "error": error_msg
            }
        
        params = {
            "query": query,
            "category": "finance"
        }
        
        try:
            # Double-check base_url is valid before making request
            if not self.base_url or not isinstance(self.base_url, str) or not self.base_url.strip():
                error_msg = f"Invalid base_url: {repr(self.base_url)}"
                logging.error(f"QuarkSearch: {error_msg}")
                raise ValueError(error_msg)
            
            # Ensure base_url is a valid string
            url_str = str(self.base_url).strip()
            if not url_str:
                error_msg = "base_url is empty after stripping"
                logging.error(f"QuarkSearch: {error_msg}")
                raise ValueError(error_msg)
            
            logging.info(f"QuarkSearch: Searching for '{query}' at {url_str}")
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url_str, json=params)
                response.raise_for_status()
                result = response.json()  # Use .json() instead of json.loads(response.text)
                search_output = result.get("result", [])
                
                search_results = []
                for content in search_output:
                    title = content.get("title", "")
                    link = content.get("link", "")
                    snippet = content.get("snippet", "")
                    
                    # 应用域名过滤
                    if not self._is_allowed_domain(link):
                        logging.info(f"Filtered out domain: {link}")
                        continue
                    
                    # 清理文本
                    title = self._clean_text(title)
                    snippet = self._clean_text(snippet)
                    
                    # 转换为 Tavily 兼容格式
                    search_results.append({
                        "title": title,
                        "url": link,
                        "content": snippet,
                        "published_date": None,  # QuarkSearch 不提供日期
                        "score": None
                    })
                    
                    # 限制结果数量
                    if len(search_results) >= max_results:
                        break
                
                return {
                    "success": len(search_results) > 0,
                    "results": search_results,
                    "answer": "",  # QuarkSearch 不提供直接答案
                    "images": [],  # QuarkSearch 不提供图片
                    "response": {
                        "query": query,
                        "results": search_results,
                        "total_results": len(search_results)
                    }
                }
                
        except Exception as e:
            logging.error(f"QuarkSearch failed: {e}")
            return {
                "success": False,
                "results": [],
                "answer": "",
                "images": [],
                "response": {},
                "error": str(e)
            }

@tool_metadata(
    display_name="Web Search",
    description="Search the internet for information, news, and research",
    icon="Search",
    color="bg-green-100 dark:bg-green-800/50",
    weight=30,
    visible=True,
    usage_guide="""
### WEB SEARCH & CONTENT EXTRACTION

**WEB SEARCH CAPABILITIES:**
- Search the web for up-to-date information with direct question answering
- **BATCH SEARCHING:** Execute multiple queries concurrently for faster research - provide an array of queries to search multiple topics simultaneously
- Retrieve relevant images related to search queries
- Get comprehensive search results with titles, URLs, and snippets
- Find recent news, articles, and information beyond training data
- Scrape webpage content for detailed information extraction when needed

**RESEARCH BEST PRACTICES:**
1. **Multi-source approach for thorough research:**
   - Start with web-search using BATCH MODE (multiple queries concurrently) to find direct answers, images, and relevant URLs efficiently
   - ALWAYS use `web_search(query=["query1", "query2", "query3"])` format when researching multiple aspects of a topic
   - Only use scrape-webpage when you need detailed content not available in search results
   - Only use browser tools when scrape-webpage fails or interaction is needed

2. **Research Workflow:**
   - **MANDATORY**: Use web-search in BATCH MODE with multiple queries for direct answers and URLs
   - **CRITICAL**: When researching any topic with multiple dimensions, ALWAYS use batch mode
   - **CORRECT FORMAT**: `web_search(query=["topic overview", "use cases", "pricing"], num_results=5)`
   - **WRONG FORMAT**: Never use `query='["topic overview", "use cases"]'` (JSON string)
   - Example: `web_search(query=["topic overview", "use cases", "pricing", "user demographics"], num_results=5)` runs all searches in parallel
   - Only if you need specific details not found in search results: use scrape-webpage on specific URLs
   - Only if scrape-webpage fails or interaction required: use browser automation tools

**WEB SEARCH BEST PRACTICES:**
- **BATCH SEARCHING FOR EFFICIENCY:** Use batch mode by providing an array of queries to execute multiple searches concurrently
- **CRITICAL FORMAT REQUIREMENTS:**
  * Single query: `web_search(query="Tesla news", num_results=5)`
  * Batch queries: `web_search(query=["Tesla news", "Tesla stock", "Tesla products"], num_results=5)`
  * The query parameter MUST be a native array, NOT a JSON string
  * num_results MUST be an integer, NOT a string
- **WHEN TO USE BATCH MODE:** Researching multiple related topics, gathering comprehensive information, parallel searches
- **WHEN TO USE SINGLE QUERY MODE:** Simple focused searches, follow-up searches, iterative refinement
- Use specific, targeted questions to get direct answers
- Include key terms and contextual information in search queries
- Filter search results by date when freshness is important
- Review the direct answer, images, and search results
- Analyze multiple search results to cross-validate information

**CONTENT EXTRACTION DECISION TREE:**
1. ALWAYS start with web-search using BATCH MODE to get direct answers and search results
2. Only use scrape-webpage when you need complete article text beyond search snippets, structured data from specific pages, or lengthy documentation
3. Never use scrape-webpage when web-search already answers the query or only basic facts are needed
4. Only use browser tools if scrape-webpage fails or interaction is required

**DATA FRESHNESS:**
- Always check publication dates of search results
- Prioritize recent sources for time-sensitive information
- Use date filters to ensure information relevance
- Provide timestamp context when sharing web search information
- Specify date ranges when searching for time-sensitive topics

**TIME CONTEXT FOR RESEARCH:**
- CRITICAL: When searching for latest news or time-sensitive information, ALWAYS use the current date/time values provided at runtime as reference points
"""
)
class SandboxWebSearchTool(SandboxToolsBase):
    """Tool for performing web searches using local QuarkSearch API and web scraping using Firecrawl."""

    def __init__(self, project_id: str, thread_manager: ThreadManager):
        super().__init__(project_id, thread_manager)
        # Load environment variables
        load_dotenv()
        # Use API keys from config
        self.firecrawl_api_key = config.FIRECRAWL_API_KEY
        self.firecrawl_url = config.FIRECRAWL_URL
        
        # Get QuarkSearch base URL from config or use default
        quark_base_url = getattr(config, 'QUARK_SEARCH_URL', None)
        # Ensure we have a valid URL (not None, not empty string)
        if not quark_base_url or not isinstance(quark_base_url, str) or not quark_base_url.strip():
            quark_base_url = 'http://192.168.1.204:9018/search'
        
        logging.info(f"Initializing QuarkSearch with URL: {quark_base_url}")
        try:
            self.quark_search = QuarkSearch(base_url=quark_base_url)
        except Exception as e:
            logging.error(f"Failed to initialize QuarkSearch: {e}")
            raise
        
        if not self.firecrawl_api_key:
            logging.warning("FIRECRAWL_API_KEY not configured - Web Scraping Tool will not be available")

        logging.info(f"Web Search Tool initialized with QuarkSearch at {quark_base_url}")

    @openapi_schema({
        "type": "function",
        "function": {
            "name": "web_search",
            "description": "Search the web for up-to-date information using local QuarkSearch API. IMPORTANT: For batch searches, pass query as a native array like [\"query1\", \"query2\"], NOT as a JSON string. For num_results, pass an integer like 5, NOT a string like \"5\". This tool supports both single and batch queries for efficient research. You can search for multiple topics simultaneously by providing an array of queries, which executes searches concurrently for faster results. Use batch mode when researching multiple related topics, gathering comprehensive information, or performing parallel searches. Results include titles, URLs, and snippets.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "oneOf": [
                            {
                                "type": "string",
                                "description": "A single search query to find relevant web pages. Be specific and include key terms to improve search accuracy. For best results, use natural language questions or keyword combinations that precisely describe what you're looking for. Example: \"Tesla latest news 2025\""
                            },
                            {
                                "type": "array",
                                "items": {
                                    "type": "string"
                                },
                                "description": "Multiple search queries to execute concurrently. CRITICAL: Pass as a native array like [\"query1\", \"query2\", \"query3\"], NOT as a JSON string. Use this for batch searching when you need to research multiple related topics simultaneously. Each query will be processed in parallel for faster results. Example: [\"Tesla news\", \"Tesla stock price\", \"Tesla products\"]"
                            }
                        ],
                        "description": "Either a single search query (string) or multiple queries (NATIVE array of strings, NOT JSON string) to execute concurrently. For batch mode, use: query=[\"query1\", \"query2\"], NOT query='[\"query1\", \"query2\"]'"
                    },
                    "num_results": {
                        "type": "integer",
                        "description": "The number of search results to return per query (1-50). MUST be a native integer like 5, NOT a string like \"5\". Increase for more comprehensive research or decrease for focused, high-relevance results. Applies to each query when using batch mode.",
                        "default": 5
                    }
                },
                "required": ["query"]
            }
        }
    })
    async def web_search(
        self, 
        query: str | list[str],
        num_results: int = 5
    ) -> ToolResult:
        """
        Search the web using local QuarkSearch API to find relevant and up-to-date information.
        Supports both single queries and batch queries for concurrent execution.
        """
        try:
            
            # Normalize num_results
            if num_results is None:
                num_results = 10
            elif isinstance(num_results, int):
                num_results = max(1, min(num_results, 50))
            elif isinstance(num_results, str):
                try:
                    num_results = max(1, min(int(num_results), 50))
                except ValueError:
                    num_results = 10
            else:
                num_results = 10

            if isinstance(query, str) and query.strip().startswith('['):
                try:
                    parsed_query = json.loads(query)
                    if isinstance(parsed_query, list):
                        query = parsed_query
                except (json.JSONDecodeError, ValueError):
                    pass
            
            is_batch = isinstance(query, list)
            
            if is_batch:
                if not query or len(query) == 0:
                    return self.fail_response("At least one search query is required in the batch.")
                
                # Filter out empty queries
                queries = [q.strip() for q in query if q and isinstance(q, str) and q.strip()]
                if not queries:
                    return self.fail_response("No valid search queries provided in the batch.")
                
                logging.info(f"Executing batch web search for {len(queries)} queries with {num_results} results each")
                
                # Execute all searches concurrently
                start_time = time.time()
                tasks = [
                    self._execute_single_search(q, num_results) 
                    for q in queries
                ]
                search_results = await asyncio.gather(*tasks, return_exceptions=True)
                elapsed_time = time.time() - start_time
                logging.info(f"Batch search completed in {elapsed_time:.2f}s (concurrent execution)")
                
                # Process results and handle exceptions
                batch_response = {
                    "batch_mode": True,
                    "total_queries": len(queries),
                    "results": []
                }
                
                all_successful = True
                for i, result in enumerate(search_results):
                    if isinstance(result, Exception):
                        logging.error(f"Error processing query '{queries[i]}': {str(result)}")
                        batch_response["results"].append({
                            "query": queries[i],
                            "success": False,
                            "error": str(result),
                            "results": [],
                            "answer": ""
                        })
                        all_successful = False
                    else:
                        batch_response["results"].append({
                            "query": queries[i],
                            "success": result.get("success", False),
                            "results": result.get("results", []),
                            "answer": result.get("answer", ""),
                            "images": result.get("images", []),
                            "response": result.get("response", {})
                        })
                        if not result.get("success", False):
                            all_successful = False
                
                logging.info(f"Batch search completed: {len([r for r in batch_response['results'] if r.get('success')])}/{len(queries)} queries successful")
                
                return ToolResult(
                    success=all_successful,
                    output=json.dumps(batch_response, ensure_ascii=False)
                )
            else:
                # Single query mode: original behavior
                if not query or not isinstance(query, str):
                    return self.fail_response("A valid search query is required.")
                
                query = query.strip()
                if not query:
                    return self.fail_response("A valid search query is required.")
                
                logging.info(f"Executing web search for query: '{query}' with {num_results} results")
                result = await self._execute_single_search(query, num_results)
                
                if result.get("success", False):
                    return ToolResult(
                        success=True,
                        output=json.dumps(result.get("response", {}), ensure_ascii=False)
                    )
                else:
                    logging.warning(f"No search results or answer found for query: '{query}'")
                    return ToolResult(
                        success=False,
                        output=json.dumps(result.get("response", {}), ensure_ascii=False)
                    )
        
        except Exception as e:
            error_message = str(e)
            query_str = ", ".join(query) if isinstance(query, list) else str(query)
            logging.error(f"Error performing web search for '{query_str}': {error_message}")
            simplified_message = f"Error performing web search: {error_message[:200]}"
            if len(error_message) > 200:
                simplified_message += "..."
            return self.fail_response(simplified_message)
    
    async def _execute_single_search(self, query: str, num_results: int) -> dict:
        """
        Helper function to execute a single search query using QuarkSearch.
        
        Parameters:
        - query: The search query string
        - num_results: Number of results to return
        
        Returns:
        - dict with success status, results, answer, images, and full response
        """
        try:
            # Use QuarkSearch instead of Tavily
            search_result = await self.quark_search.search(
                query=query,
                max_results=num_results,
                snippet_length=1000
            )
            
            # Extract results
            results = search_result.get('results', [])
            answer = search_result.get('answer', '')
            images = search_result.get('images', [])
            success = search_result.get('success', False)
            response = search_result.get('response', {})
            
            logging.info(f"Retrieved search results for query: '{query}' - {len(results)} results")
            
            return {
                "success": success,
                "results": results,
                "answer": answer,
                "images": images,
                "response": response
            }
        
        except Exception as e:
            error_message = str(e)
            logging.error(f"Error executing search for '{query}': {error_message}")
            return {
                "success": False,
                "results": [],
                "answer": "",
                "images": [],
                "response": {},
                "error": error_message
            }

    @openapi_schema({
        "type": "function",
        "function": {
            "name": "scrape_webpage",
            "description": "Extract full text content from multiple webpages in a single operation. IMPORTANT: You should ALWAYS collect multiple relevant URLs from web-search results and scrape them all in a single call for efficiency. This tool saves time by processing multiple pages simultaneously rather than one at a time. The extracted text includes the main content of each page without HTML markup by default, but can optionally include full HTML if needed for structure analysis.",
            "parameters": {
                "type": "object",
                "properties": {
                    "urls": {
                        "type": "string",
                        "description": "Multiple URLs to scrape, separated by commas. You should ALWAYS include several URLs when possible for efficiency. Example: 'https://example.com/page1,https://example.com/page2,https://example.com/page3'"
                    },
                    "include_html": {
                        "type": "boolean",
                        "description": "Whether to include the full raw HTML content alongside the extracted text. Set to true when you need to analyze page structure, extract specific HTML elements, or work with complex layouts. Default is false for cleaner text extraction.",
                        "default": False
                    }
                },
                "required": ["urls"]
            }
        }
    })
    async def scrape_webpage(
        self,
        urls: str,
        include_html: bool = False
    ) -> ToolResult:
        """
        Retrieve the complete text content of multiple webpages in a single efficient operation.
        
        ALWAYS collect multiple relevant URLs from search results and scrape them all at once
        rather than making separate calls for each URL. This is much more efficient.
        
        Parameters:
        - urls: Multiple URLs to scrape, separated by commas
        - include_html: Whether to include full HTML content alongside markdown (default: False)
        """
        try:
            # Check if Firecrawl API key is configured
            if not self.firecrawl_api_key:
                return self.fail_response("Web Scraping is not available. FIRECRAWL_API_KEY is not configured.")
            
            logging.info(f"Starting to scrape webpages: {urls}")
            
            # Ensure sandbox is initialized
            await self._ensure_sandbox()
            
            # Parse the URLs parameter
            if not urls:
                logging.warning("Scrape attempt with empty URLs")
                return self.fail_response("Valid URLs are required.")
            
            # Split the URLs string into a list
            url_list = [url.strip() for url in urls.split(',') if url.strip()]
            
            if not url_list:
                logging.warning("No valid URLs found in the input")
                return self.fail_response("No valid URLs provided.")
                
            if len(url_list) == 1:
                logging.warning("Only a single URL provided - for efficiency you should scrape multiple URLs at once")
            
            logging.info(f"Processing {len(url_list)} URLs: {url_list}")
            
            # Process each URL concurrently and collect results
            start_time = time.time()
            tasks = [self._scrape_single_url(url, include_html) for url in url_list]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            elapsed_time = time.time() - start_time
            logging.info(f"Scraped {len(url_list)} URLs in {elapsed_time:.2f}s (concurrent execution)")

            # Process results, handling exceptions
            processed_results = []
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    logging.error(f"Error processing URL {url_list[i]}: {str(result)}")
                    processed_results.append({
                        "url": url_list[i],
                        "success": False,
                        "error": str(result)
                    })
                else:
                    processed_results.append(result)
            
            results = processed_results

            
            # Summarize results
            successful = sum(1 for r in results if r.get("success", False))
            failed = len(results) - successful
            
            # Create success/failure message
            if successful == len(results):
                message = f"Successfully scraped all {len(results)} URLs. Results saved to:"
                for r in results:
                    if r.get("file_path"):
                        message += f"\n- {r.get('file_path')}"
            elif successful > 0:
                message = f"Scraped {successful} URLs successfully and {failed} failed. Results saved to:"
                for r in results:
                    if r.get("success", False) and r.get("file_path"):
                        message += f"\n- {r.get('file_path')}"
                message += "\n\nFailed URLs:"
                for r in results:
                    if not r.get("success", False):
                        message += f"\n- {r.get('url')}: {r.get('error', 'Unknown error')}"
            else:
                error_details = "; ".join([f"{r.get('url')}: {r.get('error', 'Unknown error')}" for r in results])
                return self.fail_response(f"Failed to scrape all {len(results)} URLs. Errors: {error_details}")
            
            return ToolResult(
                success=True,
                output=message
            )
        
        except Exception as e:
            error_message = str(e)
            logging.error(f"Error in scrape_webpage: {error_message}")
            return self.fail_response(f"Error processing scrape request: {error_message[:200]}")
    
    async def _scrape_single_url(self, url: str, include_html: bool = False) -> dict:
        """
        Helper function to scrape a single URL and return the result information.
        
        Parameters:
        - url: URL to scrape
        - include_html: Whether to include full HTML content alongside markdown
        """
        
        # # Add protocol if missing
        # if not (url.startswith('http://') or url.startswith('https://')):
        #     url = 'https://' + url
        #     logging.info(f"Added https:// protocol to URL: {url}")
            
        logging.info(f"Scraping single URL: {url}")
        
        try:
            # ---------- Firecrawl scrape endpoint ----------
            logging.info(f"Sending request to Firecrawl for URL: {url}")
            async with httpx.AsyncClient() as client:
                headers = {
                    "Authorization": f"Bearer {self.firecrawl_api_key}",
                    "Content-Type": "application/json",
                }
                # Determine formats to request based on include_html flag
                formats = ["markdown"]
                if include_html:
                    formats.append("html")
                
                payload = {
                    "url": url,
                    "formats": formats
                }
                
                # Use longer timeout and retry logic for more reliability
                max_retries = 3
                timeout_seconds = 30
                retry_count = 0
                
                while retry_count < max_retries:
                    try:
                        logging.info(f"Sending request to Firecrawl (attempt {retry_count + 1}/{max_retries})")
                        response = await client.post(
                            f"{self.firecrawl_url}/v1/scrape",
                            json=payload,
                            headers=headers,
                            timeout=timeout_seconds,
                        )
                        response.raise_for_status()
                        data = response.json()
                        logging.info(f"Successfully received response from Firecrawl for {url}")
                        break
                    except (httpx.ReadTimeout, httpx.ConnectTimeout, httpx.ReadError) as timeout_err:
                        retry_count += 1
                        logging.warning(f"Request timed out (attempt {retry_count}/{max_retries}): {str(timeout_err)}")
                        if retry_count >= max_retries:
                            raise Exception(f"Request timed out after {max_retries} attempts with {timeout_seconds}s timeout")
                        # Exponential backoff
                        logging.info(f"Waiting {2 ** retry_count}s before retry")
                        await asyncio.sleep(2 ** retry_count)
                    except Exception as e:
                        # Don't retry on non-timeout errors
                        logging.error(f"Error during scraping: {str(e)}")
                        raise e

            # Format the response
            title = data.get("data", {}).get("metadata", {}).get("title", "")
            markdown_content = data.get("data", {}).get("markdown", "")
            html_content = data.get("data", {}).get("html", "") if include_html else ""
            
            logging.info(f"Extracted content from {url}: title='{title}', content length={len(markdown_content)}" + 
                        (f", HTML length={len(html_content)}" if html_content else ""))
            
            formatted_result = {
                "title": title,
                "url": url,
                "text": markdown_content
            }
            
            # Add HTML content if requested and available
            if include_html and html_content:
                formatted_result["html"] = html_content
            
            # Add metadata if available
            if "metadata" in data.get("data", {}):
                formatted_result["metadata"] = data["data"]["metadata"]
                logging.info(f"Added metadata: {data['data']['metadata'].keys()}")
            
            # Create a simple filename from the URL domain and date
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # Extract domain from URL for the filename
            from urllib.parse import urlparse
            parsed_url = urlparse(url)
            domain = parsed_url.netloc.replace("www.", "")
            
            # Clean up domain for filename
            domain = "".join([c if c.isalnum() else "_" for c in domain])
            safe_filename = f"{timestamp}_{domain}.json"
            
            logging.info(f"Generated filename: {safe_filename}")
            
            # Save results to a file in the /workspace/scrape directory
            scrape_dir = f"{self.workspace_path}/scrape"
            await self.sandbox.fs.create_folder(scrape_dir, "755")
            
            results_file_path = f"{scrape_dir}/{safe_filename}"
            json_content = json.dumps(formatted_result, ensure_ascii=False, indent=2)
            logging.info(f"Saving content to file: {results_file_path}, size: {len(json_content)} bytes")
            
            await self.sandbox.fs.upload_file(
                json_content.encode(),
                results_file_path,
            )
            
            return {
                "url": url,
                "success": True,
                "title": title,
                "file_path": results_file_path,
                "content_length": len(markdown_content)
            }
        
        except Exception as e:
            error_message = str(e)
            logging.error(f"Error scraping URL '{url}': {error_message}")
            
            # Create an error result
            return {
                "url": url,
                "success": False,
                "error": error_message
            }


if __name__ == "__main__":
    async def test_web_search():
        """Test function for the web search tool"""
        # This test function is not compatible with the sandbox version
        print("Test function needs to be updated for sandbox version")
    
    async def test_scrape_webpage():
        """Test function for the webpage scrape tool"""
        # This test function is not compatible with the sandbox version
        print("Test function needs to be updated for sandbox version")
    
    async def run_tests():
        """Run all test functions"""
        await test_web_search()
        await test_scrape_webpage()
        
    asyncio.run(run_tests())