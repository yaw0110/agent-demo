from demo4.ReflectionAgent import ReflectionAgent
from demo3.HelloAgentsLLM import HelloAgentsLLM

llm = HelloAgentsLLM()
agent = ReflectionAgent(llm)

task = '编写一个Python函数，找出1到n之间所有的素数 (prime numbers)。'

agent.run(task)