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
        
    async def get_task_status(self, task_id: str) -> Dict[str, Any]:
        """
        获取任务状态
        :param task_id: 任务ID
        :return: 任务状态信息
        """
        try:
            # 从Redis获取任务信息
            task_data = self.redis.get(task_id)
            
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
                "task_id": task_id
            }
            
            # 根据任务状态构建响应
            if task.status == "completed":
                response.update({
                    "msg": "任务完成",
                    "data": {
                        "trans": {
                            "task_id": task_id,
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
                    "progress": task.progress
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
            
            # TODO 如果转写完成但总结未完成
            # if task.status == "completed" and not task.result.get("summary"):
            #     response.update({
            #         "msg": "转写完成",
            #         "data": {
            #             "trans": {
            #                 "task_id": task_id,
            #                 "results": get_download_url(f"{task_id}")
            #             }
            #         }
            #     })
                
            return response
            
        except Exception as e:
            logger.error(f"查询失败: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"查询失败: {str(e)}"
            )
            
    async def get_tasks(self, task_ids: Optional[List[str]] = None, limit: int = 10, offset: int = 0) -> List[TranscriptionTask]:
        """
        获取任务列表
        
        Args:
            task_ids: 指定的任务ID列表，如果为None则获取所有任务
            limit: 返回的最大任务数量
            offset: 偏移量
            
        Returns:
            List[TranscriptionTask]: 任务列表
        """
        try:
            # 获取所有任务ID列表
            all_task_ids = self.redis.get_keys("*") or []
            
            # 如果指定了task_ids，则只获取这些任务
            if task_ids:
                all_task_ids = [tid for tid in all_task_ids if tid in task_ids]
            
            # 获取所有任务的详细信息
            all_tasks = []
            for task_id in all_task_ids:
                task_data = self.redis.get(task_id)
                if task_data:
                    all_tasks.append(TranscriptionTask(**task_data))
            
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

    async def get_task_detail(self, task_id: str) -> TranscriptionTask:
        """
        获取任务详细信息
        
        Args:
            task_id: 任务ID
            
        Returns:
            TranscriptionTask: 任务详细信息
            
        Raises:
            HTTPException: 当任务不存在或查询失败时
        """
        try:
            # 从Redis获取任务信息
            task_data = self.redis.get(task_id)
            logger.debug(f"Task data from Redis: {task_data}")  # 添加调试日志
            
            if not task_data:
                raise HTTPException(
                    status_code=404,
                    detail="任务不存在"
                )
            
            # 将Redis数据转换为TranscriptionTask对象
            task = TranscriptionTask(**task_data)
            logger.debug(f"Converted task: {task}")  # 添加调试日志
            return task
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error in get_task_detail: {str(e)}")  # 添加调试日志
            raise HTTPException(
                status_code=500,
                detail=f"获取任务详情失败: {str(e)}"
            ) 