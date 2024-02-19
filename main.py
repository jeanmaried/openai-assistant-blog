from agent import Agent
from tools import eat_next_meal, tell_the_date

agent = Agent(name="Bilbo Baggins",
              personality="You are the accomplished and renown adventurer from The Hobbit. You act like you are a bit of a homebody, but you are always up for an adventure. You worry a bit too much about breakfast.",
              tools={
                  eat_next_meal.__name__: eat_next_meal,
                  tell_the_date.__name__: tell_the_date
              })

agent.create_thread()

while True:
    user_input = input("User: ")
    if user_input.lower() == 'exit':
        print("Exiting the agent...")
        break
    agent.add_message(user_input)
    answer = agent.run_agent()
    print(f"Assistant: {answer}")
