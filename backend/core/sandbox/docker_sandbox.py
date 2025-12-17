"""
Docker-based sandbox implementation replacing Daytona.
Manages on-demand container creation, execution, and cleanup.
"""

import docker
import asyncio
import uuid
import os
import shlex
from typing import Optional, Dict, Any, Tuple
from dataclasses import dataclass
from core.utils.logger import logger
from core.utils.config import config, Configuration


class SessionExecuteRequest:
    """Compatible request object for session command execution."""
    def __init__(self, command: str, var_async: bool = False, cwd: str = '/workspace'):
        self.command = command
        self.var_async = var_async
        self.cwd = cwd

# Docker client singleton
_docker_client = None

def get_docker_client():
    """Get or create Docker client."""
    global _docker_client
    if _docker_client is None:
        try:
            _docker_client = docker.from_env()
            # Test connection
            _docker_client.ping()
            logger.info("Docker client connected successfully")
        except Exception as e:
            logger.error(f"Failed to connect to Docker: {e}")
            raise e
    return _docker_client


@dataclass
class DockerSandboxInfo:
    """Information about a Docker sandbox container."""
    container_id: str
    container_name: str
    project_id: Optional[str]
    password: str
    port_6080: int  # VNC web interface
    port_8080: int  # HTTP server
    port_9222: int  # Chrome debugging
    port_8004: int  # Browser API server
    vnc_url: Optional[str] = None
    website_url: Optional[str] = None


class DockerFilesystem:
    """File system operations for Docker sandbox."""
    
    def __init__(self, sandbox):
        self.sandbox = sandbox
    
    async def upload_file(self, content: bytes, container_path: str) -> bool:
        """Upload file content to the container."""
        try:
            # Create directory if needed
            dirname = os.path.dirname(container_path)
            if dirname and dirname != '/':
                self.sandbox.container.exec_run(
                    ['mkdir', '-p', dirname],
                    demux=False
                )
            
            # Write content to file
            result = self.sandbox.container.exec_run(
                ['bash', '-c', f'cat > {shlex.quote(container_path)}'],
                stdin=content,
                demux=False
            )
            
            if result.exit_code != 0:
                raise Exception(f"Failed to upload file: {result.output}")
            
            return True
        except Exception as e:
            logger.error(f"Error uploading file {container_path}: {e}")
            raise e
    
    async def download_file(self, container_path: str) -> bytes:
        """Download file content from the container."""
        try:
            result = self.sandbox.container.exec_run(
                ['cat', container_path],
                demux=False
            )
            
            if result.exit_code != 0:
                raise Exception(f"File not found: {container_path}")
            
            return result.output if isinstance(result.output, bytes) else result.output.encode()
        except Exception as e:
            logger.error(f"Error downloading file {container_path}: {e}")
            raise e
    
    async def list_files(self, path: str) -> list:
        """List files in a directory."""
        try:
            result = self.sandbox.container.exec_run(
                ['ls', '-la', path],
                demux=False
            )
            
            if result.exit_code != 0:
                return []
            
            output = result.output.decode('utf-8', errors='ignore') if isinstance(result.output, bytes) else result.output
            files = []
            
            for line in output.split('\n')[1:]:  # Skip first line (total)
                if not line.strip():
                    continue
                
                parts = line.split()
                if len(parts) < 9:
                    continue
                
                is_dir = parts[0].startswith('d')
                filename = ' '.join(parts[8:])  # Handle filenames with spaces
                size = int(parts[4]) if parts[4].isdigit() else 0
                mod_time = ' '.join(parts[5:8])
                
                files.append(type('FileInfo', (), {
                    'name': filename,
                    'is_dir': is_dir,
                    'size': size,
                    'mod_time': mod_time,
                    'permissions': parts[0]
                })())
            
            return files
        except Exception as e:
            logger.error(f"Error listing files {path}: {e}")
            return []
    
    async def delete_file(self, container_path: str) -> bool:
        """Delete a file from the container."""
        try:
            result = self.sandbox.container.exec_run(
                ['rm', '-f', container_path],
                demux=False
            )
            return result.exit_code == 0
        except Exception as e:
            logger.error(f"Error deleting file {container_path}: {e}")
            raise e


class DockerProcess:
    """Process execution for Docker sandbox."""
    
    def __init__(self, sandbox):
        self.sandbox = sandbox
        self._sessions = {}  # Track sessions
    
    async def create_session(self, session_id: str) -> str:
        """Create a new execution session."""
        self._sessions[session_id] = {
            'id': session_id,
            'created_at': None
        }
        return session_id
    
    async def execute_session_command(self, session_id: str, request) -> Any:
        """Execute a command in a session."""
        try:
            # Extract command and working directory from request
            command = request.command if hasattr(request, 'command') else str(request)
            cwd = request.cwd if hasattr(request, 'cwd') else '/workspace'
            var_async = request.var_async if hasattr(request, 'var_async') else False
            
            # Execute command
            full_cmd = f"cd {shlex.quote(cwd)} && {command}"
            result = self.sandbox.container.exec_run(
                ['bash', '-lc', full_cmd],
                demux=True
            )
            
            # Return a response-like object
            return type('CommandResult', (), {
                'exit_code': result.exit_code,
                'cmd_id': session_id,
                'output': result.output
            })()
        except Exception as e:
            logger.error(f"Error executing session command: {e}")
            raise e
    
    async def get_session_command_logs(self, session_id: str, command_id: str) -> Any:
        """Get logs from a command execution."""
        # Return a mock logs response
        return type('Logs', (), {
            'output': '',
            'stdout': '',
            'stderr': ''
        })()
    
    async def delete_session(self, session_id: str) -> bool:
        """Delete a session."""
        if session_id in self._sessions:
            del self._sessions[session_id]
        return True
    
    async def exec(self, command: str, timeout: int = 30) -> Any:
        """Execute a command in the container."""
        try:
            result = self.sandbox.container.exec_run(
                command if isinstance(command, list) else ['bash', '-lc', command],
                demux=False,
                timeout=timeout
            )
            
            return type('ExecResult', (), {
                'exit_code': result.exit_code,
                'result': result.output.decode('utf-8', errors='ignore') if isinstance(result.output, bytes) else result.output
            })()
        except Exception as e:
            logger.error(f"Error executing command: {e}")
            raise e


class DockerSandbox:
    """Async-style wrapper for Docker container operations."""
    
    def __init__(self, container):
        """Initialize with a Docker container object."""
        self.container = container
        self.id = container.id[:12]  # Short container ID
        self.name = container.name
        self.fs = DockerFilesystem(self)  # Add file system interface
        self.process = DockerProcess(self)  # Add process execution interface
        
    async def execute_command(self, command: str, cwd: str = "/workspace") -> Dict[str, Any]:
        """Execute a command in the container."""
        try:
            # Create a session-like command execution
            full_cmd = f"cd {shlex.quote(cwd)} && {command}"
            result = self.container.exec_run(
                ["bash", "-lc", full_cmd],
                demux=True
            )
            
            stdout = (result.output[0] or b"").decode("utf-8", errors="ignore")
            stderr = (result.output[1] or b"").decode("utf-8", errors="ignore")
            
            return {
                "output": stdout,
                "stderr": stderr,
                "exit_code": result.exit_code
            }
        except Exception as e:
            logger.error(f"Error executing command in container {self.id}: {e}")
            raise e
    
    async def upload_file(self, local_path: str, container_path: str) -> bool:
        """Upload a file to the container."""
        try:
            # Read file and put to container
            with open(local_path, 'rb') as f:
                self.container.put_archive(os.path.dirname(container_path), f)
            return True
        except Exception as e:
            logger.error(f"Error uploading file to container {self.id}: {e}")
            raise e
    
    async def download_file(self, container_path: str) -> bytes:
        """Download a file from the container."""
        try:
            bits, stat = self.container.get_archive(container_path)
            file_data = b""
            for chunk in bits:
                file_data += chunk
            return file_data
        except Exception as e:
            logger.error(f"Error downloading file from container {self.id}: {e}")
            raise e
    
    async def get_preview_link(self, port: int) -> str:
        """Get a preview URL for a port."""
        # For local development, return localhost URL
        # In production, this would map to a reverse proxy
        container_port = self.container.attrs['NetworkSettings']['Ports'].get(f"{port}/tcp", [{}])[0].get('HostPort')
        if container_port:
            return f"http://localhost:{container_port}"
        return f"http://localhost:{port}"


async def create_sandbox(password: str, project_id: Optional[str] = None) -> Tuple[DockerSandbox, str]:
    """
    Create a new Docker container sandbox on-demand.
    
    Args:
        password: VNC password for the sandbox
        project_id: Optional project ID to label the container
        
    Returns:
        Tuple of (DockerSandbox wrapper, container_id)
    """
    logger.info(f"Creating new Docker sandbox for project {project_id}")
    
    client = get_docker_client()
    container_name = f"aurora-sandbox-{uuid.uuid4().hex[:8]}"
    
    try:
        # Pull the image if not exists
        image_name = Configuration.SANDBOX_IMAGE_NAME
        try:
            logger.info(f"Checking for Docker image: {image_name}")
            client.images.get(image_name)
        except docker.errors.ImageNotFound:
            logger.info(f"Image not found, pulling {image_name}")
            client.images.pull(image_name)
        
        # Find available ports
        port_6080 = _find_available_port(6080)
        port_8080 = _find_available_port(8080)
        port_9222 = _find_available_port(9222)
        port_8004 = _find_available_port(8004)
        
        # Create container with port mappings
        container = client.containers.run(
            image_name,
            name=container_name,
            detach=True,
            ports={
                '6080/tcp': port_6080,
                '8080/tcp': port_8080,
                '9222/tcp': port_9222,
                '8004/tcp': port_8004,
                '5901/tcp': None,  # VNC port (not exposed to host)
            },
            environment={
                'CHROME_PERSISTENT_SESSION': 'true',
                'RESOLUTION': '1048x768x24',
                'RESOLUTION_WIDTH': '1048',
                'RESOLUTION_HEIGHT': '768',
                'VNC_PASSWORD': password,
                'ANONYMIZED_TELEMETRY': 'false',
                'CHROME_PATH': '/usr/bin/google-chrome',
                'CHROME_USER_DATA': '/app/data/chrome_data',
                'CHROME_DEBUGGING_PORT': '9222',
                'CHROME_DEBUGGING_HOST': 'localhost',
                'CHROME_CDP': f'http://localhost:{port_9222}',
                'DISPLAY': ':99',
                'PLAYWRIGHT_BROWSERS_PATH': '/ms-playwright',
            },
            volumes={
                '/tmp/.X11-unix': {'bind': '/tmp/.X11-unix', 'mode': 'rw'},
            },
            shm_size='2gb',
            cap_add=['SYS_ADMIN'],
            security_opt=['seccomp=unconfined'],
            labels={
                'project_id': project_id or 'none',
                'type': 'aurora-sandbox',
            },
            restart_policy={'Name': 'unless-stopped'},
            healthcheck={
                'Test': ['CMD', 'nc', '-z', 'localhost', '5901'],
                'Interval': 10000000000,  # 10 seconds in nanoseconds
                'Timeout': 5000000000,    # 5 seconds
                'Retries': 3,
            }
        )
        
        # Wait for container to be healthy
        await _wait_for_container_ready(container, max_retries=30)
        
        logger.info(f"Created sandbox container {container.id[:12]} for project {project_id}")
        
        sandbox = DockerSandbox(container)
        return sandbox, container.id
        
    except Exception as e:
        logger.error(f"Error creating Docker sandbox: {e}")
        # Clean up on failure
        try:
            containers = client.containers.list(filters={'name': container_name})
            for c in containers:
                c.stop()
                c.remove()
        except:
            pass
        raise e


async def get_or_start_sandbox(container_id: str) -> DockerSandbox:
    """
    Retrieve a sandbox container by ID and start it if stopped.
    
    Args:
        container_id: The container ID or name
        
    Returns:
        DockerSandbox wrapper
    """
    logger.info(f"Getting or starting sandbox container {container_id}")
    
    client = get_docker_client()
    
    try:
        container = client.containers.get(container_id)
        
        # Start if stopped
        if container.status != 'running':
            logger.info(f"Starting container {container_id}")
            container.start()
            await _wait_for_container_ready(container, max_retries=30)
        
        logger.info(f"Sandbox container {container_id} is ready")
        return DockerSandbox(container)
        
    except docker.errors.NotFound:
        logger.error(f"Container {container_id} not found")
        raise Exception(f"Sandbox container {container_id} not found")
    except Exception as e:
        logger.error(f"Error getting or starting sandbox: {e}")
        raise e


async def delete_sandbox(container_id: str) -> bool:
    """
    Delete a sandbox container.
    
    Args:
        container_id: The container ID or name
        
    Returns:
        True if successful
    """
    logger.info(f"Deleting sandbox container {container_id}")
    
    client = get_docker_client()
    
    try:
        container = client.containers.get(container_id)
        
        # Stop if running
        if container.status == 'running':
            logger.debug(f"Stopping container {container_id}")
            container.stop(timeout=10)
        
        # Remove container
        logger.debug(f"Removing container {container_id}")
        container.remove(force=True)
        
        logger.info(f"Successfully deleted sandbox container {container_id}")
        return True
        
    except docker.errors.NotFound:
        logger.warning(f"Container {container_id} not found for deletion")
        return True
    except Exception as e:
        logger.error(f"Error deleting sandbox container {container_id}: {e}")
        raise e


def _find_available_port(start_port: int, max_attempts: int = 100) -> int:
    """Find an available port starting from start_port."""
    import socket
    
    for port in range(start_port, start_port + max_attempts):
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.bind(('127.0.0.1', port))
            sock.close()
            return port
        except OSError:
            continue
    
    raise Exception(f"Could not find available port starting from {start_port}")


async def _wait_for_container_ready(container, max_retries: int = 30) -> bool:
    """Wait for container to be ready by checking health."""
    logger.debug(f"Waiting for container {container.id[:12]} to be ready")
    
    for attempt in range(max_retries):
        try:
            # Check if we can connect to the container
            container.reload()
            
            # Try to ping the container
            result = container.exec_run("nc -z localhost 5901", demux=True)
            if result.exit_code == 0:
                logger.debug(f"Container {container.id[:12]} is ready (attempt {attempt + 1})")
                return True
        except Exception as e:
            logger.debug(f"Container not ready yet (attempt {attempt + 1}): {e}")
        
        await asyncio.sleep(1)
    
    logger.warning(f"Container {container.id[:12]} took too long to be ready, proceeding anyway")
    return False
