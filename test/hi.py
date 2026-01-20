from tavily import TavilyClient

tavily_client = TavilyClient(api_key="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")
response = tavily_client.search("What kind of place is Guangzhou?")

print(response)