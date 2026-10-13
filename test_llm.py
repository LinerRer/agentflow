from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage
from config.settings import LLM_MODEL_NAME

print(f"测试模型：{LLM_MODEL_NAME}")
llm = ChatOllama(model=LLM_MODEL_NAME, temperature=0.7)

try:
    resp = llm.invoke([HumanMessage(content="说一句你好")])
    print("✅ 大模型调用成功")
    print("返回内容：", resp.content)
except Exception as e:
    print("❌ 调用失败")
    import traceback
    traceback.print_exc()
