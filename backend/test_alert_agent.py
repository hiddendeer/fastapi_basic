"""
测试报警 Agent 接口

运行方式（在 backend 目录下）:
    uv run python test_alert_agent.py
"""
import asyncio
import httpx

BASE_URL = "http://localhost:8000/api/v1"

async def test_alert_agent():
    """测试报警处理接口"""
    async with httpx.AsyncClient(timeout=120.0) as client:
        # 测试用例列表
        test_cases = [
            {"alert_message": "仓库着火了"},
            {"alert_message": "办公室发现烟雾"},
            {"alert_message": "换衣间漏水"},
            {"alert_message": "机房温度过高"},
        ]

        for i, test_case in enumerate(test_cases, 1):
            print(f"\n{'='*60}")
            print(f"测试用例 {i}: {test_case['alert_message']}")
            print('='*60)

            try:
                response = await client.post(
                    f"{BASE_URL}/alert-agent/alert",
                    json=test_case
                )

                if response.status_code == 200:
                    data = response.json()
                    print(f"原始报警: {data['original_alert']}")

                    if data['tool_calls']:
                        print(f"\n工具调用记录:")
                        for tool_call in data['tool_calls']:
                            print(f"  - 工具: {tool_call['tool_name']}")
                            print(f"    输入: {tool_call['tool_input']}")
                            output = tool_call['tool_output']
                            if len(output) > 100:
                                output = output[:100] + "..."
                            print(f"    输出: {output}")

                    if data['contact_info']:
                        print(f"\n联系信息: {data['contact_info']}")

                    if data['emergency_manuals']:
                        print(f"\n应急手册查询: {data['emergency_manuals'][:200]}...")

                    print(f"\n检修建议:\n{data['maintenance_suggestion']}")
                else:
                    print(f"请求失败: {response.status_code}")
                    print(f"错误详情: {response.text}")
            except Exception as e:
                print(f"测试出错: {e}")

async def test_health_check():
    """测试健康检查接口"""
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(f"{BASE_URL}/alert-agent/health")
            print(f"健康检查: {response.json()}")
        except Exception as e:
            print(f"健康检查失败: {e}")

if __name__ == "__main__":
    print("开始测试报警 Agent...")
    asyncio.run(test_health_check())
    asyncio.run(test_alert_agent())
    print("\n测试完成！")
