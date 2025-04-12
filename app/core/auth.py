import httpx
from fastapi import Request, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional
from app.core.config import settings

security = HTTPBearer()

async def verify_jwt(request: Request, auth: HTTPAuthorizationCredentials = None) -> bool:
    """
    验证JWT token
    
    Args:
        request: FastAPI请求对象
        auth: Bearer token凭证
        
    Returns:
        bool: 验证是否通过
        
    Raises:
        HTTPException: 当验证失败时抛出相应的异常
    """
    if not auth:
        raise HTTPException(status_code=401, detail="未提供认证信息")
    
    jwt_token = auth.credentials
    original_uri = str(request.url.path)
    
    # 准备请求头
    headers = {
        "Authorization": f"Bearer {jwt_token}",
        "X-Original-URI": original_uri
    }
    
    try:
        # 发起验证请求
        async with httpx.AsyncClient(timeout=settings.JWT_VERIFY_TIMEOUT) as client:
            response = await client.get(
                settings.JWT_VERIFY_URL,
                headers=headers
            )
            
        if response.status_code == 200:
            return True
        elif response.status_code == 401:
            raise HTTPException(
                status_code=401,
                detail="JWT令牌已过期或解密失败"
            )
        elif response.status_code == 403:
            raise HTTPException(
                status_code=403,
                detail="所属资源不属于请求的用户或者用户未激活"
            )
        else:
            raise HTTPException(
                status_code=response.status_code,
                detail=f"验证服务返回错误: {response.text}"
            )
    except httpx.TimeoutException:
        raise HTTPException(
            status_code=504,
            detail="验证服务请求超时"
        )
    except httpx.RequestError as e:
        raise HTTPException(
            status_code=500,
            detail=f"验证服务请求失败: {str(e)}"
        )

async def jwt_auth_middleware(request: Request):
    """
    JWT认证中间件
    """
    # 从请求头中获取认证信息
    auth_header = request.headers.get("Authorization")
    if not auth_header:
        raise HTTPException(status_code=401, detail="未提供认证信息")
    
    try:
        scheme, credentials = auth_header.split()
        if scheme.lower() != "bearer":
            raise HTTPException(status_code=401, detail="无效的认证方案")
        
        auth = HTTPAuthorizationCredentials(scheme=scheme, credentials=credentials)
        await verify_jwt(request, auth)
        
    except ValueError:
        raise HTTPException(status_code=401, detail="无效的认证格式") 