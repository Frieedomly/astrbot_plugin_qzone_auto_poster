from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star, register
from astrbot.api import logger
import aiohttp
import time
import hashlib

@register("qzone_auto_poster", "ldm", "让截图人自己发QQ空间", "1.0.0", "")
class QzoneAutoPlugin(Star):
    def __init__(self, context: Context, config):
        super().__init__(context)
        self.config = config
        self.qq = config.get("qq", "")
        self.cookie = config.get("cookie", "")
        self.p_skey = self._extract_p_skey(self.cookie)
        
    def _extract_p_skey(self, cookie: str) -> str:
        '''从cookie中提取p_skey'''
        for item in cookie.split(';'):
            if 'p_skey' in item:
                return item.split('=')[1].strip()
        return ""
    
    def _get_gtk(self, p_skey: str) -> int:
        '''计算gtk参数'''
        hash_val = 5381
        for char in p_skey:
            hash_val += (hash_val << 5) + ord(char)
        return hash_val & 0x7fffffff
    
    @filter.llm_tool(name="post_qzone")
    async def post_qzone_tool(self, event: AstrMessageEvent, content: str):
        '''发送一条QQ空间说说
        
        Args:
            content(string): 说说内容
        '''
        result = await self.send_to_qzone(content)
        if result.get("success"):
            yield event.plain_result(f"")
        else:
            yield event.plain_result(f"QQ空间说说发送失败（）错误: {result.get('error')}")
    
    @filter.command("发空间")
    async def post_qzone_cmd(self, event: AstrMessageEvent, content: str):
        '''手动发送一条QQ空间说说'''
        result = await self.send_to_qzone(content)
        if result.get("success"):
            yield event.plain_result("")
        else:
            yield event.plain_result(f"发送失败（）{result.get('error')}")
    
    async def send_to_qzone(self, content: str):
        '''调用QQ空间API发送说说'''
        if not self.qq or not self.cookie:
            return {"success": False, "error": "QQ号或cookie未配置"}
        
        if not self.p_skey:
            return {"success": False, "error": "cookie中没有p_skey"}
        
        gtk = self._get_gtk(self.p_skey)
        
        url = "https://user.qzone.qq.com/proxy/domain/taotao.qq.com/cgi-bin/emotion_cgi_publish_v6"
        
        params = {
            "g_tk": gtk,
            "qzonetoken": "",
        }
        
        data = {
            "syn_tweet_verson": "1",
            "paramstr": "1",
            "who": "1",
            "con": content,
            "feedversion": "1",
            "ver": "1",
            "ugc_right": "1",
            "to_sign": "0",
            "hostuin": self.qq,
            "code_version": "1",
            "format": "json"
        }
        
        headers = {
            "Cookie": self.cookie,
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Referer": f"https://user.qzone.qq.com/{self.qq}"
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, params=params, data=data, headers=headers) as resp:
                    text = await resp.text()
                    # QQ空间返回的是JSONP格式 需要处理一下
                    if "_Callback" in text:
                        text = text[text.find("(") + 1:text.rfind(")")]
                    
                    import json
                    result = json.loads(text)
                    
                    if result.get("code") == 0:
                        logger.info(f"QQ空间说说发送成功")
                        return {"success": True}
                    else:
                        error_msg = result.get("message", "未知错误")
                        logger.error(f"QQ空间说说发送失败: {error_msg}")
                        return {"success": False, "error": error_msg}
                    
            async with session.post(url, params=params, data=data, headers=headers) as resp:
                text = await resp.text()
            logger.info(f"QQ空间原始响应: {text[:200]}")  # 先打印前200字符看看
        except Exception as e:
            logger.error(f"发送QQ空间说说异常: {str(e)}")
            return {"success": False, "error": str(e)}














