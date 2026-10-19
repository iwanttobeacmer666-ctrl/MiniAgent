from agent import run_agent
def main() ->None:
    text=input("请输入你的任务:")
    if  text.strip() == "":
        print("任务不能为空")
        return 
    text=text.strip()
    print(f"收到任务: {text}")
    # main 负责输入输出；run_agent 负责模型请求、工具执行和消息历史。
    answer = run_agent(text)
    print(f"模型回答: {answer}")
    
if __name__ == "__main__":
   main()
