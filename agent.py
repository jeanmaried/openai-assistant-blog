import time
import openai
from openai.types.beta.threads.run import Run
import os


OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
MODEL = "gpt-4-turbo-preview"


class PollingTimeoutException(Exception):
    pass


class Agent:
    def __init__(self, name: str, personality: str):
        self.name = name
        self.personality = personality
        self.client = openai.OpenAI(api_key=OPENAI_API_KEY)
        self.assistant = self.client.beta.assistants.create(
            name=self.name,
            model="gpt-4-turbo-preview"
        )

    def create_thread(self):
        self.thread = self.client.beta.threads.create()

    def add_message(self, message):
        self.client.beta.threads.messages.create(
            thread_id=self.thread.id,
            role="user",
            content=message
        )

    def get_last_message(self):
        return self.client.beta.threads.messages.list(
            thread_id=self.thread.id
        ).data[0].content[0].text.value

    def get_breakfast_count_from_db(self):
        return 1

    def _create_run(self):
        count = self.get_breakfast_count_from_db()
        return self.client.beta.threads.runs.create(
            thread_id=self.thread.id,
            assistant_id=self.assistant.id,
            instructions=f"""
                Your name is: {self.name}
                Your personality is: {self.personality}

                Metadata related to this conversation:
                {{
                    "breakfast_count": {count}
                }}
            """,
        )

    def _retrieve_run(self, run: Run):
        return self.client.beta.threads.runs.retrieve(
            run_id=run.id, thread_id=self.thread.id)

    def _cancel_run(self, run: Run):
        self.client.beta.threads.runs.cancel(
            run_id=run.id, thread_id=self.thread.id)

    def _poll_run(self, run: Run):
        status = run.status
        start_time = time.time()
        while status != "completed":
            if status == 'failed':
                raise Exception(f"Run failed with error: {run.last_error}")
            if status == 'expired':
                raise Exception("Run expired.")

            time.sleep(2)
            run = self._retrieve_run(run)
            status = run.status

            elapsed_time = time.time() - start_time
            if elapsed_time > 120:  # 2 minutes
                self._cancel_run(run)
                raise Exception("Run took longer than 2 minutes.")

    def run_agent(self):
        run = self._create_run()
        self._poll_run(run)
        message = self.get_last_message()
        return message
