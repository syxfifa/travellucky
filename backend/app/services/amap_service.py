"""高德地图MCP服务封装"""

import threading
from typing import List, Dict, Any, Optional
from hello_agents.tools import MCPTool
from ..config import get_settings
from ..models.schemas import Location, POIInfo, WeatherInfo

# 全局MCP工具实例
_amap_mcp_tool = None
# 路由层现在会经 asyncio.to_thread 从多个工作线程调用本模块的取实例函数，
# 因此「检查-构造-赋值」这段必须加锁（详见 get_amap_service 的注释）。
_amap_mcp_tool_lock = threading.Lock()


def get_amap_mcp_tool() -> MCPTool:
    """
    获取高德地图MCP工具实例(单例模式)
    
    Returns:
        MCPTool实例
    """
    global _amap_mcp_tool
    
    if _amap_mcp_tool is None:
        with _amap_mcp_tool_lock:
            if _amap_mcp_tool is None:
                settings = get_settings()

                if not settings.vite_amap_web_key:
                    raise ValueError("高德地图 API Key 未配置，请先在前端设置页完成配置")

                # 创建MCP工具
                _amap_mcp_tool = MCPTool(
                    name="amap",
                    description="高德地图服务,支持POI搜索、路线规划、天气查询等功能",
                    server_command=["amap-mcp-server"],
                    env={"AMAP_MAPS_API_KEY": settings.vite_amap_web_key},
                    auto_expand=True  # 自动展开为独立工具
                )

                print(f"✅ 高德地图MCP工具初始化成功")
                print(f"   工具数量: {len(_amap_mcp_tool._available_tools)}")

                # 打印可用工具列表
                if _amap_mcp_tool._available_tools:
                    print("   可用工具:")
                    for tool in _amap_mcp_tool._available_tools[:5]:  # 只打印前5个
                        print(f"     - {tool.get('name', 'unknown')}")
                    if len(_amap_mcp_tool._available_tools) > 5:
                        print(f"     ... 还有 {len(_amap_mcp_tool._available_tools) - 5} 个工具")

    return _amap_mcp_tool


class AmapService:
    """REST implementation for HTTP routes; agents retain the installed MCP tool."""
    def __init__(self):
        self.key = get_settings().vite_amap_web_key
        if not self.key:
            raise ValueError("VITE_AMAP_WEB_KEY is not configured")

    def _request(self, endpoint, **params):
        import httpx
        try:
            response = httpx.get("https://restapi.amap.com/v3/" + endpoint,
                params={"key": self.key, **params}, timeout=15, trust_env=False)
            response.raise_for_status()
            data = response.json()
        except Exception:
            raise RuntimeError("高德请求失败，请检查网络") from None
        if data.get("status") != "1":
            raise RuntimeError("高德服务错误: " + str(data.get("infocode", "unknown")))
        return data

    @staticmethod
    def _location(value):
        if not value or not isinstance(value, str):
            return None
        longitude, latitude = map(float, value.split(","))
        return Location(longitude=longitude, latitude=latitude)

    def search_poi(self, keywords, city, citylimit=True):
        data = self._request("place/text", keywords=keywords, city=city,
                             citylimit=str(citylimit).lower(), extensions="all")
        result = []
        for poi in data.get("pois", []):
            location = self._location(poi.get("location"))
            if location:
                result.append(POIInfo(id=poi["id"], name=poi["name"],
                    type=poi.get("type") or "", address=poi.get("address") or "",
                    location=location, tel=poi.get("tel") or None))
        return result

    def geocode(self, address, city=None):
        data = self._request("geocode/geo", address=address, city=city or "")
        items = data.get("geocodes", [])
        return self._location(items[0].get("location")) if items else None

    def get_weather(self, city):
        district = self._request("config/district", keywords=city, subdistrict=0)
        districts = district.get("districts", [])
        if not districts:
            return []
        data = self._request("weather/weatherInfo", city=districts[0]["adcode"], extensions="all")
        result = []
        for forecast in data.get("forecasts", []):
            for cast in forecast.get("casts", []):
                result.append(WeatherInfo(date=cast["date"], city=city,
                    day_weather=cast.get("dayweather", ""), night_weather=cast.get("nightweather", ""),
                    day_temp=cast.get("daytemp", 0), night_temp=cast.get("nighttemp", 0),
                    wind_direction=cast.get("daywind", ""), wind_power=cast.get("daypower", "")))
        return result

    def plan_route(self, origin_address, destination_address, origin_city=None,
                   destination_city=None, route_type="walking"):
        if route_type not in {"walking", "driving", "transit"}:
            raise ValueError("Unsupported route type")
        origin = self.geocode(origin_address, origin_city)
        destination = self.geocode(destination_address, destination_city)
        if not origin or not destination:
            return {}
        params = {"origin":f"{origin.longitude},{origin.latitude}",
                  "destination":f"{destination.longitude},{destination.latitude}"}
        endpoint = "direction/" + route_type
        if route_type == "transit":
            if not origin_city:
                raise ValueError("Transit requires origin_city")
            endpoint = "direction/transit/integrated"
            params.update(city=origin_city, cityd=destination_city or origin_city)
        data = self._request(endpoint, **params)
        route = data.get("route", {})
        paths = route.get("transits" if route_type == "transit" else "paths", [])
        return paths[0] if paths else {}

    def get_poi_detail(self, poi_id):
        return self._request("place/detail", id=poi_id, extensions="all")


# 创建全局服务实例
_amap_service = None
_amap_service_lock = threading.Lock()


def get_amap_service() -> AmapService:
    """获取高德地图服务实例(单例模式)"""
    global _amap_service

    if _amap_service is None:
        # 加锁的原因：路由层现在通过 asyncio.to_thread(get_amap_service) 调用本函数，
        # 并发首次请求会同时进入这里。若不加锁，「检查 - 构造 - 赋值」之间存在窗口，
        # 多个线程会各建一个 AmapService（每次构造都包含一次 MCP 服务发现往返），
        # 后写入的覆盖先写入的，多出来的实例被直接丢弃。
        with _amap_service_lock:
            if _amap_service is None:
                _amap_service = AmapService()

    return _amap_service


def reset_amap_service() -> None:
    """重置高德地图服务与 MCP 工具实例（用于运行时配置更新后热生效）。"""
    global _amap_service, _amap_mcp_tool
    with _amap_service_lock:
        _amap_service = None
    with _amap_mcp_tool_lock:
        _amap_mcp_tool = None
