from typing import Optional, Dict, Any
from fastapi import HTTPException
from app.core.config import settings
from app.utils.storage import RedisStorage
from app.schemas.transcription import TranscriptionTask

class TaskStatusService:
    def __init__(self):
        self.redis = RedisStorage(prefix="transcription:")
        
    async def get_task_status(self, task_id: str) -> Dict[str, Any]:
        """
        获取任务状态
        :param task_id: 任务ID
        :return: 任务状态信息x
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
                            "results": f"{settings.BASE_URL}{settings.DOWNLOAD_URL_PREFIX}/{task_id}.json"
                        },
                        "summary": {
                            "task_id": task_id,
                            "results": f"{settings.BASE_URL}{settings.DOWNLOAD_URL_PREFIX}/{task_id}-summary.md"
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
            #                 "results": f"{settings.BASE_URL}{settings.DOWNLOAD_URL_PREFIX}/{task_id}.json"
            #             }
            #         }
            #     })
                
            return response
            
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"查询失败: {str(e)}"
            ) 