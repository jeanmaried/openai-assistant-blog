import json
import time
import openai
from openai.types.beta.threads.run import Run
import os
import docstring_parser
import db

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
MODEL = "gpt-4-turbo-preview"


class Agent:
    def __init__(self, name: str, personality: str, tools: list[callable]):
        self.name = name
        self.personality = personality
        self.client = openai.OpenAI(api_key=OPENAI_API_KEY)

        self.callable_tools_dict = self._create_function_dict(tools)
        self.assistant = self.client.beta.assistants.create(
            name=self.name,
            model="gpt-4-turbo-preview",
            tools=self._convert_functions_to_open_ai_format(tools)
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
        return db.breakfast_count

    def _convert_functions_to_open_ai_format(self, functions: list[callable]):
        # Note that we don't handle None because you wouldn't set the type of an expected argument to None
        # Note we only handle python types that are valid in JSON
        python_type_to_json_type = {
            "str": "string",
            "int": "number",
            "float": "number",
            "bool": "boolean",
            "list": "array",
            "dict": "object"
        }

        return [
            {
                "type": "function",
                "function": {
                    "name": function.__name__,
                    "description": docstring_parser.parse(function.__doc__).short_description,
                    "parameters": {
                        "type": "object",
                        "properties": {
                            p.arg_name: {
                                "type": python_type_to_json_type.get(p.type_name, "string"),
                                "description": p.description
                            }
                            for p in docstring_parser.parse(function.__doc__).params
                            if p.arg_name != "self"
                        },
                        "required": [
                            p.arg_name
                            for p in docstring_parser.parse(function.__doc__).params
                            if p.arg_name != "self" and not p.is_optional
                        ]
                    }
                }
            }
            for function in functions
        ]

    def _create_function_dict(self, functions: list[callable]) -> dict[str, callable]:
        return {function.__name__: function for function in functions}

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

    def _call_tools(self, run_id: str, tool_calls: list[dict]):
        tool_outputs = []

        for tool_call in tool_calls:
            id, function = tool_call.id, tool_call.function
            function_args = json.loads(function.arguments)
            function_to_call = self.callable_tools_dict[function.name]
            function_response = function_to_call(**function_args)
            tool_outputs.append(
                {"tool_call_id": id, "output": function_response})

        self.client.beta.threads.runs.submit_tool_outputs(
            thread_id=self.thread.id,
            run_id=run_id,
            tool_outputs=tool_outputs
        )

    def _poll_run(self, run: Run):
        status = run.status
        start_time = time.time()
        while status != "completed":
            if status == 'failed':
                raise Exception(f"Run failed with error: {run.last_error}")
            if status == 'expired':
                raise Exception("Run expired.")
            if status == 'requires_action':
                self._call_tools(
                    run.id, run.required_action.submit_tool_outputs.tool_calls)

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
