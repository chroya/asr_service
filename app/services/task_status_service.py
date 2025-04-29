import logging
from typing import Optional, Dict, Any, List
from fastapi import HTTPException
from app.core.config import settings
from app.services.redis_service import RedisService
from app.schemas.transcription import TranscriptionTask
from app.utils import get_download_url

logger = logging.getLogger(__name__)

class TaskStatusService:
    def __init__(self):
        redis_service = RedisService()
        self.redis = redis_service.get_client(prefix="transcription:")
        
    async def get_task_status(self, uni_key: str) -> Dict[str, Any]:
        """
        获取任务状态
        :param uni_key: 任务唯一标识符
        :return: 任务状态信息
        """
        try:
            # 获取任务数据
            task_data = self.redis.get(uni_key)
            if not task_data:
                return {
                    "code": -4,
                    "msg": "此任务还未上传",
                    "upload_url": settings.UPLOAD_URL
                }
            
            # 将Redis数据转换为TranscriptionTask对象
            task = TranscriptionTask(**task_data)
            
            # 构建基础响应
            response = {
                "code": task.code,
                "task_id": task.task_id
            }
            
            # 根据任务状态构建响应
            if task.status == "completed":
                response.update({
                    "msg": "任务完成",
                    "data": {
                        "trans": {
                            "task_id": task.task_id,
                            "results": get_download_url(f"{task.result_path}")
                        }
                    }
                })
            elif task.status == "pending":
                response.update({
                    "code": 1,
                    "msg": "正在上传，待开始转写"
                })
            elif task.status == "processing":
                response.update({
                    "code": 2,
                    "msg": "上传完成，正在转写",
                    "progress": task.progress,
                    "progress_message": task.progress_message
                })
            elif task.status == "failed":
                if task.code == -1:
                    response.update({
                        "msg": "上传文件失败"
                    })
                elif task.code == -2:
                    response.update({
                        "msg": "转写失败，请重新转写"
                    })
                elif task.code == -3:
                    response.update({
                        "msg": "总结生成失败"
                    })
                else:
                    response.update({
                        "msg": task.message or "处理失败"
                    })
            
            return response
            
        except Exception as e:
            logger.error(f"查询失败: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"查询失败: {str(e)}"
            )
            
    async def get_tasks(self, uni_keys: Optional[List[str]] = None, limit: int = 10, offset: int = 0) -> List[TranscriptionTask]:
        """
        获取任务列表
        
        Args:
            uni_keys: 指定的任务唯一标识符列表，如果为None则获取所有任务
            limit: 返回的最大任务数量
            offset: 偏移量
            
        Returns:
            List[TranscriptionTask]: 任务列表
        """
        try:
            # 获取所有任务
            all_tasks = []
            for key in self.redis.get_keys("*"):
                task_data = self.redis.get(key)
                if task_data:
                    # 确保task_data包含uni_key字段
                    if 'uni_key' not in task_data:
                        task_data['uni_key'] = key
                    task = TranscriptionTask(**task_data)
                    if not uni_keys or task.uni_key in uni_keys:
                        all_tasks.append(task)
            
            # 按创建时间倒序排序所有任务
            all_tasks.sort(key=lambda x: x.created_at, reverse=True)
            
            # 分页
            tasks = all_tasks[offset:offset + limit]
            
            return tasks
            
        except Exception as e:
            logger.error(f"获取任务列表失败: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"获取任务列表失败: {str(e)}"
            )

    async def get_task_detail(self, uni_key: str) -> TranscriptionTask:
        """
        获取任务详细信息
        
        Args:
            uni_key: 任务唯一标识符
            
        Returns:
            TranscriptionTask: 任务详细信息
            
        Raises:
            HTTPException: 当任务不存在或查询失败时
        """
        try:
            # 获取任务数据
            task_data = self.redis.get(uni_key)
            if not task_data:
                raise HTTPException(
                    status_code=404,
                    detail="任务不存在"
                )
            
            # 将Redis数据转换为TranscriptionTask对象
            task = TranscriptionTask(**task_data)
            return task
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error in get_task_detail: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"获取任务详情失败: {str(e)}"
            ) 